/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package v1alpha2_test

import (
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = DescribeTable("Validate ConfigMapSource",
	func(name, errStr string) {
		Expect(strings.Join(paasv1alpha2.ConfigMapSource{Name: name}.Validate(), ",")).To(ContainSubstring(errStr))
	},
	Entry("invalid", "Normal", "a lowercase RFC 1123 subdomain"),
	Entry("invalid", "abc_test", "a lowercase RFC 1123 subdomain"),
	Entry("invalid", "", "a lowercase RFC 1123 subdomain"),
)
