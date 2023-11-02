# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, Optional

from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.core.region.states import get_region
from paasng.platform.applications.constants import AppLanguage, ApplicationType
from paasng.platform.applications.exceptions import IntegrityError
from paasng.platform.applications.models import Application, UserMarkedApplication
from paasng.platform.applications.signals import application_logo_updated, prepare_change_application_name
from paasng.platform.applications.specs import AppTypeSpecs
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.serializers import MinimalModuleSLZ, ModuleSLZ, ModuleSourceConfigSLZ
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n
from paasng.utils.validators import RE_APP_SEARCH

from .fields import ApplicationField, AppNameField
from .mixins import AdvancedCreationParamsMixin, AppBasicInfoMixin, MarketParamsMixin


class CreateApplicationV2SLZ(AppBasicInfoMixin):
    """新版创建应用表单，支持更丰富的自定义选项"""

    type = serializers.ChoiceField(choices=ApplicationType.get_django_choices(), default=ApplicationType.DEFAULT.value)
    engine_enabled = serializers.BooleanField(default=True, required=False)
    engine_params = ModuleSourceConfigSLZ(required=False)
    advanced_options = AdvancedCreationParamsMixin(required=False)

    def validate(self, attrs):
        super().validate(attrs)

        if attrs['engine_enabled'] and not attrs.get('engine_params'):
            raise ValidationError(_('应用引擎参数未提供'))

        # Be compatible with current application creation page, should be removed when new design was published
        if not attrs['engine_enabled']:
            attrs['type'] = ApplicationType.ENGINELESS_APP.value
        elif attrs['type'] == ApplicationType.ENGINELESS_APP.value:
            raise ValidationError(_('已开启引擎，类型不能为 "engineless_app"'))

        self._validate_source_init_template(attrs)
        return attrs

    def _validate_source_init_template(self, attrs):
        """'source_init_template' can only be optional for some special application types"""
        type_specs = AppTypeSpecs.get_by_type(ApplicationType(attrs['type']))
        if type_specs.require_templated_source and not attrs.get('engine_params', {}).get('source_init_template'):
            raise ValidationError(_('engine_params.source_init_template: 必须选择一个应用模板'))


class CreateThirdPartyApplicationSLZ(AppBasicInfoMixin):
    """创建外链应用的表单"""

    engine_enabled = serializers.BooleanField(default=False)
    market_params = MarketParamsMixin()

    def validate(self, attrs):
        if attrs['engine_enabled']:
            raise ValidationError(_('该接口只支持创建外链应用'))
        return attrs


class SysThirdPartyApplicationSLZ(AppBasicInfoMixin):
    """创建系统外链应用"""

    operator = serializers.CharField(required=True)

    def validate_code(self, code):
        sys_id = self.context.get('sys_id')
        if sys_id not in settings.ALLOW_THIRD_APP_SYS_ID_LIST:
            raise ValidationError(f"系统({sys_id})未被允许创建外链应用")

        # 应用ID 必现以 "系统ID-" 为前缀
        prefix = f"{sys_id}-"
        if not code.startswith(prefix):
            raise ValidationError(f"应用ID 必须以 {prefix} 为前缀")
        return code


@i18n
class UpdateApplicationSLZ(serializers.Serializer):
    """Serializer for update application"""

    name = I18NExtend(AppNameField(max_length=20, help_text="应用名称"))

    def _validate_duplicated_field(self, data):
        """Universal validate method for code and name"""
        # Send signal, when console_db if given, this function call will raise
        # ValidationError if name is duplicated.
        # 仅修改对应语言的应用名称
        update_fields = {}
        if get_language() == "zh-cn":
            update_fields["name"] = data["name_zh_cn"]
        elif get_language() == "en":
            update_fields["name_en"] = data["name_en"]

        try:
            prepare_change_application_name.send(sender=self.__class__, code=self.instance.code, **update_fields)
        except IntegrityError as e:
            detail = {e.field: [_("{}已经被占用").format(e.get_field_display())]}
            raise ValidationError(detail=detail)
        return data

    def validate(self, data):
        return self._validate_duplicated_field(data)

    def update(self, instance, validated_data):
        # 仅修改对应语言的应用名称, 如果前端允许同时填写中英文的应用名称, 则可以去掉该逻辑.
        if get_language() == "zh-cn":
            instance.name = validated_data['name_zh_cn']
        elif get_language() == "en":
            instance.name_en = validated_data['name_en']
        instance.save()
        return instance


class SearchApplicationSLZ(serializers.Serializer):
    keyword = serializers.RegexField(RE_APP_SEARCH, max_length=20, default="", allow_blank=False)
    include_inactive = serializers.BooleanField(default=False)
    prefer_marked = serializers.BooleanField(default=True)


class EnvironmentDeployInfoSLZ(serializers.Serializer):
    deployed = serializers.BooleanField(help_text=u"是否部署")
    url = serializers.URLField(help_text=u"访问地址")


class ApplicationSLZ(serializers.ModelSerializer):
    name = TranslatedCharField()
    region_name = serializers.CharField(read_only=True, source='get_region_display', help_text="应用版本名称")
    logo_url = serializers.CharField(read_only=True, source='get_logo_url', help_text="应用的 Logo 地址")
    config_info = serializers.DictField(read_only=True, help_text='应用的额外状态信息')
    modules = serializers.SerializerMethodField(help_text='应用各模块信息列表')

    def get_modules(self, application: Application):
        # 将 default_module 排在第一位
        modules = application.modules.all().order_by('-is_default', '-created')
        return ModuleSLZ(modules, many=True).data

    class Meta:
        model = Application
        exclude = ['logo']


class ApplicationWithDeployInfoSLZ(ApplicationSLZ):
    deploy_info = serializers.JSONField(read_only=True, source='_deploy_info', help_text=u"部署状态")


class ApplicationRelationSLZ(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()

    def to_internal_value(self, data):
        """将属性转换为 validated_data 的方法， 直接将其赋值为 application 来通过验证"""
        return data


class ApplicationListDetailedSLZ(serializers.Serializer):
    """Serializer for detailed app list"""

    valid_order_by_fields = ('code', 'created', 'latest_operated_at', 'name')
    exclude_collaborated = serializers.BooleanField(default=False)
    include_inactive = serializers.BooleanField(default=False)
    region = serializers.ListField(required=False)
    language = serializers.ListField(required=False)
    search_term = serializers.CharField(required=False)
    source_origin = serializers.ChoiceField(required=False, allow_null=True, choices=SourceOrigin.get_choices())
    type = serializers.ChoiceField(choices=ApplicationType.get_django_choices(), required=False)
    order_by = serializers.CharField(default='name')
    prefer_marked = serializers.BooleanField(default=True)

    def validate_order_by(self, value):
        if value.startswith('-'):
            value = '-%s' % value.lstrip('-')

        if value.lstrip('-') not in self.valid_order_by_fields:
            raise ValidationError(u'无效的排序选项：%s' % value)
        return value

    @staticmethod
    def _validate_choice(value_list, choice):
        choice_key = [c[0] for c in choice]
        for value in value_list:
            if value not in choice_key:
                raise ValidationError(_("无效的选项: %s") % value)
        return value_list

    def validate_region(self, value_list):
        return self._validate_choice(value_list, get_region().get_choices())

    def validate_language(self, value_list):
        return self._validate_choice(value_list, AppLanguage.get_django_choices())

    def validate_source_origin(self, value: Optional[int]):
        if value:
            return SourceOrigin(value)

    def validate_type(self, value: Optional[str]):
        if value:
            return ApplicationType(value)


class ApplicationListMinimalSLZ(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)
    source_origin = serializers.ChoiceField(
        choices=SourceOrigin.get_choices(), default=None, allow_blank=True, allow_null=True
    )


class ApplicationGroupFieldSLZ(serializers.Serializer):
    """Serializer for detailed app list"""

    include_inactive = serializers.BooleanField(default=False)
    field = serializers.CharField(default="region")

    def validate_field(self, value):
        if value not in ["region", "language"]:
            raise ValidationError(_("无效的分类选项: %s") % value)
        return value


class ProductSLZ(serializers.Serializer):
    name = serializers.CharField()
    logo = serializers.CharField(source='get_logo_url')


class MarketConfigSLZ(serializers.Serializer):
    # 第三方应用直接打开应用地址，不需要打开应用市场的地址
    source_tp_url = serializers.URLField(required=False, allow_blank=True, allow_null=True, help_text="第三方访问地址")


class ApplicationWithMarketSLZ(serializers.Serializer):
    application = ApplicationWithDeployInfoSLZ(read_only=True)
    product = ProductSLZ(read_only=True)
    marked = serializers.BooleanField(read_only=True)
    market_config = MarketConfigSLZ(read_only=True)


class ApplicationMinimalSLZ(serializers.ModelSerializer):
    name = TranslatedCharField()

    class Meta:
        model = Application
        fields = ['id', 'code', 'name']


class ApplicationSLZ4Record(serializers.ModelSerializer):
    """用于操作记录"""

    name = TranslatedCharField()
    logo_url = serializers.CharField(read_only=True, source='get_logo_url', help_text=u"应用的Logo地址")
    config_info = serializers.DictField(read_only=True, help_text='应用额外状态信息')

    class Meta:
        model = Application
        fields = ['id', 'code', 'name', 'logo_url', 'config_info']


class MarketAppMinimalSLZ(serializers.Serializer):
    name = serializers.CharField()


class ApplicationWithMarketMinimalSLZ(serializers.Serializer):
    application = ApplicationMinimalSLZ(read_only=True)
    product = MarketAppMinimalSLZ(read_only=True)


class ApplicationMarkedSLZ(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api.user.mark.applications.detail', lookup_field='code', help_text=u"单条记录访问链接"
    )

    application_code = serializers.ReadOnlyField(source="application.code", help_text=u"应用编码")
    application_name = serializers.ReadOnlyField(source="application.code", help_text=u"应用名称")
    application = ApplicationField(
        slug_field='code',
        many=False,
        allow_null=True,
        help_text="应用id",
    )

    def validate(self, attrs):
        if self.context["request"].method in ["POST"]:
            if self.Meta.model.objects.filter(
                owner=self.context["request"].user.pk, application__code=attrs["application"].code
            ).exists():
                raise serializers.ValidationError(u'您已经标记该应用')
        return attrs

    class Meta:
        model = UserMarkedApplication
        fields = ['application_code', 'application_name', "application", "url"]

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user.pk
        return super(ApplicationMarkedSLZ, self).create(validated_data)

    def __repr__(self):
        return self.application_name


class ModuleEnvSLZ(serializers.Serializer):
    module = MinimalModuleSLZ()
    environment = serializers.CharField()


class ApplicationFeatureFlagSLZ(serializers.Serializer):
    name = serializers.CharField()
    effect = serializers.BooleanField()


class ProtectionStatusSLZ(serializers.Serializer):
    """Serialize app resource protection status"""

    activated = serializers.BooleanField(help_text='是否激活保护')
    reason = serializers.CharField(help_text='具体原因')


class ApplicationLogoSLZ(serializers.ModelSerializer):
    """Serializer for representing and modifying Logo"""

    logo = serializers.ImageField(write_only=True)
    logo_url = serializers.ReadOnlyField(source="get_logo_url", help_text=u"应用 Logo 访问地址")
    code = serializers.ReadOnlyField(help_text=u"应用 Code")

    class Meta:
        model = Application
        fields = ['logo', 'logo_url', 'code']

    @atomic
    def update(self, instance: Application, validated_data: Dict) -> Dict:
        result = super().update(instance, validated_data)
        # Send signal to trigger extra processes for logo
        application_logo_updated.send(sender=instance, application=instance)
        return result