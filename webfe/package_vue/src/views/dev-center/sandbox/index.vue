<template>
  <div
    class="bk-apps-wrapper sandbox-container"
    :style="{
      'padding-top': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 50 : 50}px`,
    }"
  >
    <section class="top-bar card-style">
      <div class="title">
        <span>{{ $t('应用') }}：</span>
        <bk-breadcrumb>
          <bk-breadcrumb-item
            v-for="(item, index) in breadcrumbList"
            :key="index"
            :class="{ fore: item.title !== $t('沙箱开发') }"
          >
            {{ item.title }}
          </bk-breadcrumb-item>
        </bk-breadcrumb>
      </div>
      <div
        class="back"
        @click="back"
      >
        <i class="paasng-icon paasng-arrows-left icon-cls-back mr5"></i>
        <span>{{ $t('返回') }}</span>
      </div>
    </section>
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="sandbox-loading"
      :height="450"
    >
      <div class="sandbox-content">
        <div class="top-box">
          <bk-button
            :theme="'primary'"
            @click="showRequestDialog"
          >
            {{ $t('获取沙箱环境密码') }}
          </bk-button>
          <bk-alert
            type="warning"
            class="sandbox-alert-cls"
          >
            <div slot="title">
              <span>{{ $t('沙箱环境仅用于临时在线调试，如果沙箱环境在 2 个小时内没有任何操作，将自动被销毁。') }}</span>
              <bk-popconfirm
                trigger="click"
                ext-cls="sandbox-destroy-cls"
                width="288"
                @confirm="handleSandboxDestruction"
              >
                <div slot="content">
                  <div class="custom">
                    <i class="bk-icon icon-info-circle-shape pr5 content-icon"></i>
                    <div class="content-text">{{ $t('确认销毁沙箱开发环境吗？') }}</div>
                  </div>
                </div>
                <bk-button
                  :theme="'primary'"
                  text
                  size="small"
                >
                  {{ $t('立即销毁') }}
                </bk-button>
              </bk-popconfirm>
            </div>
          </bk-alert>
        </div>
        <section :class="['sandbox-editor', { collapse: !isCollapse }, { 'is-footer': isLoadingSandbox }]">
          <bk-resize-layout
            placement="right"
            :min="360"
            :initial-divide="360"
            :border="false"
            ext-cls="sandbox-resize-layout"
          >
            <div
              slot="main"
              class="iframe-box"
            >
              <iframe
                v-if="isLoadingSandbox"
                ref="iframeRef"
                id="iframe-embed"
                :src="iframeUrl"
                scrolling="no"
                frameborder="0"
              />
              <div
                v-else
                class="iframe-loading"
              >
                <img src="/static/images/loading.gif" />
                <p>{{ $t('沙箱环境正在启动，预计需要约 1 分钟，请稍候。') }}</p>
              </div>
            </div>
            <!-- 登录展示沙盒后，展示右侧的tab信息 -->
            <right-tab
              slot="aside"
              ref="rightTabRef"
              class="right-tab-cls"
              :data="sandboxData"
              :service-name="serviceName"
              :buildLog="buildLog"
              :runLog="runLog"
              :loading="isLogsLoading"
              :env="env"
              @tab-change="rightTabChange"
              @collapse-change="handleRightTabCollapseChange"
            />
          </bk-resize-layout>
        </section>
      </div>
      <section
        v-if="isLoadingSandbox"
        class="footer-tools-box"
      >
        <!-- 运行状态 -->
        <div
          class="run-tip"
          v-if="buildStatus && ['Failed', 'Success'].includes(buildStatus)"
        >
          <bk-alert
            :type="isBuildSuccess ? 'success' : 'error'"
            :title="isBuildSuccess ? $t('运行成功') : $t('运行失败')"
            closable
          ></bk-alert>
        </div>
        <div class="left">
          <template v-if="isProcessRunning || isBuildSuccess">
            <bk-button
              :theme="'default'"
              :loading="isRunNowLoading"
              @click="handleRunNow"
            >
              <i class="paasng-icon paasng-refresh-line"></i>
              {{ $t('重新运行') }}
            </bk-button>
          </template>
          <template v-else>
            <bk-button
              :theme="'primary'"
              :loading="isRunNowLoading"
              bk-trace="{id: 'sandbox', action: 'run', category: '云原生应用'}"
              @click="showRunSandboxDialog"
            >
              <i class="paasng-icon paasng-right-shape"></i>
              {{ $t('立即运行') }}
            </bk-button>
          </template>
          <bk-button
            :theme="'default'"
            class="ml8"
            @click="showSubmitCodeDialog"
          >
            {{ $t('提交代码') }}
          </bk-button>
        </div>
        <!-- 访问链接 -->
        <bk-button
          v-if="isProcessRunning || isBuildSuccess"
          :theme="'primary'"
          text
          @click="handleVisitNow"
        >
          {{ $t('立即访问') }}
          <i class="paasng-icon paasng-jump-link"></i>
        </bk-button>
      </section>
    </paas-content-loader>
    <!-- 密码获取 -->
    <password-request-dialog
      :show.sync="isDialogVisible"
      :passwrod="sandboxPassword"
    />
    <!-- 立即运行二次确认 -->
    <run-sandbox-dialog
      :show.sync="isRunSandboxVisible"
      :process-data="processData"
      @confirm="handleRunNow"
    />
    <!-- 提交代码 -->
    <submit-code-dialog
      ref="submitCodeDialog"
      :show.sync="isSubmitCodeVisible"
      :config="submitCode"
      @submit="submitCommit"
      @reset="submitCodeReset"
    />
  </div>
</template>

<script>
import PasswordRequestDialog from './comps/password-request-dialog.vue';
import RightTab from './comps/right-tab.vue';
import { bus } from '@/common/bus';
import axios from 'axios';
import RunSandboxDialog from './comps/run-sandbox-dialog.vue';
import SubmitCodeDialog from './comps/submit-code-dialog.vue';

export default {
  name: 'Sandbox',
  components: {
    PasswordRequestDialog,
    RightTab,
    RunSandboxDialog,
    SubmitCodeDialog,
  },
  data() {
    return {
      isDialogVisible: false,
      sandboxData: {},
      isLoading: true,
      deployId: '',
      buildLog: '',
      runLog: '',
      isRunNowLoading: false,
      serviceName: '',
      refreshTime: {
        build: 5,
        run: 5,
      },
      buildIntervalId: null,
      runIntervalId: null,
      sandboxIntervalId: null,
      curTabActive: 'config',
      // 构建日志状态
      buildStatus: '',
      isLogsLoading: true,
      isCollapse: true,
      processInfo: {},
      processData: [],
      isRunSandboxVisible: false,
      sandboxPassword: '',
      isSubmitCodeVisible: false,
      submitCode: {
        loading: false,
        isConfirm: false,
        fileTotal: 0,
        tree: {},
      },
    };
  },
  computed: {
    code() {
      return this.$route.query.code;
    },
    module() {
      return this.$route.query.module;
    },
    env() {
      return this.$route.query.env;
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    breadcrumbList() {
      const list = [
        { title: this.code },
        { title: `${this.$t('模块')}：${this.module}` },
        { title: this.$t('沙箱开发') },
      ];
      return list;
    },
    iframeUrl() {
      const url = this.sandboxData.urls?.code_editor_url || '';
      return this.ensureHttpProtocol(url);
    },
    // 沙箱加载完成
    isLoadingSandbox() {
      return this.sandboxData.code_editor_status === 'Healthy' && this.sandboxData.dev_sandbox_status === 'Healthy';
    },
    // 构建成功
    isBuildSuccess() {
      return this.buildStatus === 'Success';
    },
    // 是否存在进程信息
    isProcessRunning() {
      return !!Object.keys(this.processInfo).length;
    },
  },
  created() {
    Promise.all([this.getSandboxWithCodeEditorData(), this.getEnhancedServices()]).finally(() => {
      setTimeout(() => {
        this.isLoading = false;
      }, 1000);
    });
    this.sandboxIntervalId = setInterval(() => {
      this.getSandboxWithCodeEditorData();
    }, 3000);
  },
  mounted() {
    // 当切换到日志tab，默认5s刷新一次日志
    bus.$on('change-refresh-time', (data) => {
      this.$set(this.refreshTime, data.key, data.value);
      this.automaticRefresh();
    });
    bus.$on('refresh-log', (type) => {
      if (this.deployId) {
        type === 'run' ? this.getRunLog() : this.getBuildLog();
      }
    });
  },
  beforeDestroy() {
    this.clearIntervals();
    clearInterval(this.sandboxIntervalId);
    bus.$off('change-refresh-time');
    bus.$off('refresh-log');
  },
  methods: {
    ensureHttpProtocol(url) {
      const protocol = window.location.protocol ?? 'http:';
      const protocolPattern = /^(https?:\/\/)/i;
      // 如果 URL 没有协议，则根据当前环境协议决定
      if (!protocolPattern.test(url)) {
        return `${protocol}//${url}`;
      }
      return url;
    },
    // 沙箱删除处理
    sandboxDeletionHandled() {
      // 沙箱已经被删除
      this.isDialogVisible = false;
      clearInterval(this.sandboxIntervalId);
      this.back();
    },
    // 获取沙箱密码
    async getSandboxPassword() {
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxPassword', {
          appCode: this.code,
          moduleId: this.module,
        });
        this.sandboxPassword = res.password;
      } catch (e) {
        if (e.code === 'DEV_SANDBOX_NOT_FOUND') {
          this.sandboxDeletionHandled();
          return;
        }
        this.catchErrorHandler(e);
      }
    },
    showRequestDialog() {
      this.sandboxPassword = '';
      this.getSandboxPassword();
      this.isDialogVisible = true;
    },
    rightTabChange(name) {
      this.curTabActive = name;
    },
    // 清除现有的计时器
    clearIntervals() {
      if (this.buildIntervalId) {
        clearInterval(this.buildIntervalId);
        this.buildIntervalId = null;
      }
      if (this.runIntervalId) {
        clearInterval(this.runIntervalId);
        this.runIntervalId = null;
      }
    },
    // 自动刷新获取日志
    automaticRefresh() {
      if (this.curTabActive !== 'log' || !this.deployId) return;
      // 右侧tab高亮切换，当高亮为日志时，需要按照对应时间自动刷新(点击立即运行后，才允许自动刷新)
      this.clearIntervals();
      this.pollingBuildLog();
      this.pollingRunLog();
    },
    // 轮询构建日志
    pollingBuildLog() {
      // 如果构建不成功，则继续获取构建日志
      if (!this.isBuildSuccess) {
        this.buildIntervalId = setInterval(() => {
          this.getBuildLog(true);
        }, this.refreshTime.build * 1000);
      }
    },
    // 轮询运行日志
    pollingRunLog() {
      // 如果运行日志的刷新时间不是 'off'，则继续获取运行日志
      if (this.refreshTime.run !== 'off') {
        this.runIntervalId = setInterval(() => {
          this.getRunLog();
        }, this.refreshTime.run * 1000);
      }
    },
    // 获取界面数据
    async getSandboxWithCodeEditorData() {
      if (this.isLoadingSandbox && this.sandboxIntervalId) {
        clearInterval(this.sandboxIntervalId);
        return;
      }
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxWithCodeEditor', {
          appCode: this.code,
          moduleId: this.module,
        });
        setTimeout(() => {
          this.sandboxData = res;
          if (this.isLoadingSandbox) {
            this.getSandboxStatus();
          }
        }, 1000);
      } catch (e) {
        if (e.code === 'DEV_SANDBOX_NOT_FOUND') {
          this.sandboxDeletionHandled();
          return;
        }
        this.catchErrorHandler(e);
      }
    },
    // 获取增强服务
    async getEnhancedServices() {
      try {
        const res = await this.$store.dispatch('sandbox/getEnhancedServices', {
          appCode: this.code,
          moduleId: this.module,
        });
        this.serviceName = res.map((service) => service.service?.display_name)?.join('、');
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 请求函数
    async executeRequest(url, method = 'get', data = null) {
      try {
        const response = await axios({
          method,
          url: this.ensureHttpProtocol(url),
          data,
          headers: {
            Authorization: `Bearer ${this.sandboxData.token}`,
          },
        });
        return response.data;
      } catch (e) {
        // 沙箱相关接口报错，通过获取密码接口判定沙箱是否已删除
        if (e.code === 'ERR_NETWORK') {
          this.getSandboxPassword();
        }
        this.catchErrorHandler(e);
        return e;
      }
    },
    // 获取当前沙箱进程状态
    async getSandboxStatus() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.urls?.devserver_url}processes/status`);
        const res = await this.executeRequest(url, 'get');
        this.processInfo = res.status || {};
        if (!!Object.keys(this.processInfo).length) {
          this.switchLogTab();
          // 轮询运行日志
          if (this.runIntervalId) {
            clearInterval(this.runIntervalId);
            this.runIntervalId = null;
          }
          this.pollingRunLog();
        }
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取沙箱进程列表
    async getSandboxProcesses() {
      const url = this.ensureHttpProtocol(`${this.sandboxData.urls?.devserver_url}processes/list`);
      const res = await this.executeRequest(url, 'get');
      this.processData = res.processes;
    },
    // 切换至日志tab
    switchLogTab() {
      this.$refs.rightTabRef.handleTabChange({ name: 'log', label: this.$t('日志') });
    },
    // 运行沙箱环境二次确认弹窗
    showRunSandboxDialog() {
      this.isRunSandboxVisible = true;
      this.getSandboxProcesses();
    },
    // 立即运行
    async handleRunNow() {
      this.isRunNowLoading = true;
      // 重置状态
      this.buildStatus = '';
      try {
        this.switchLogTab();
        const url = this.ensureHttpProtocol(`${this.sandboxData.urls?.devserver_url}deploys`);
        const res = await this.executeRequest(url, 'post');
        this.deployId = res.deployID;
        // 如果tab为折叠状态时，运行需打开
        if (!this.isCollapse) {
          this.$refs.rightTabRef.handleSwitchSide();
        }
        // 获取相关日志（构建/运行）
        this.getBuildLog();
        this.getRunLog();
        this.clearIntervals();
        this.automaticRefresh();
        this.isLogsLoading = true;
      } finally {
        setTimeout(() => {
          this.isLogsLoading = false;
        }, 300);
      }
    },
    // 获取构建日志
    async getBuildLog(isAutomaticRefresh = false) {
      if (this.isBuildSuccess && isAutomaticRefresh) return;
      try {
        const url = this.ensureHttpProtocol(
          `${this.sandboxData.urls?.devserver_url}deploys/${this.deployId}/results?log=true`
        );
        const res = await this.executeRequest(url);
        this.buildLog = res.log;
        // 构建日志成功，无需自动刷新
        this.buildStatus = res.status;
      } finally {
        this.isLogsLoading = false;
        if (this.isBuildSuccess || this.buildStatus === 'Failed') {
          this.isRunNowLoading = false;
        }
      }
    },
    // 运行日志
    async getRunLog() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.urls?.devserver_url}app_logs`);
        const res = await this.executeRequest(url);

        this.runLog = res.logs ?? '';
      } finally {
        setTimeout(() => {
          this.isLogsLoading = false;
        }, 300);
      }
    },
    handleVisitNow() {
      const url = this.ensureHttpProtocol(this.sandboxData?.urls?.app_url);
      window.open(url, '_blank');
    },
    handleRightTabCollapseChange(data) {
      this.isCollapse = data;
    },
    back() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.code,
          moduleId: 'default',
        },
      });
    },
    // 立即销毁
    async handleSandboxDestruction() {
      try {
        await this.$store.dispatch('sandbox/destroySandbox', {
          appCode: this.code,
          moduleId: this.module,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('销毁成功！'),
        });
        this.back();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    showSubmitCodeDialog() {
      this.isSubmitCodeVisible = true;
      this.getDiffs();
    },
    // 获取 diff 信息
    async getDiffs() {
      this.submitCode.loading = true;
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.urls?.devserver_url}codes/diffs?tree=true`);
        const res = await this.executeRequest(url);
        this.submitCode.isConfirm = !(res.total > 0);
        this.submitCode.fileTotal = res.total;
        this.submitCode.tree = res.tree;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitCode.loading = false;
      }
    },
    // 提交 commit 信息
    async submitCommit(message) {
      try {
        const res = await this.$store.dispatch('sandbox/sandboxSubmitCode', {
          appCode: this.code,
          moduleId: this.module,
          data: {
            message,
          },
        });
        this.showMessage(res.repo_url);
        this.isSubmitCodeVisible = false;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.$refs.submitCodeDialog?.closeLoading();
      }
    },
    // commit 成功弹窗
    showMessage(link) {
      const h = this.$createElement;
      const that = this;
      this.$bkMessage({
        message: h('p', [
          `${that.$t('代码提交成功')}，`,
          h(
            'a',
            {
              attrs: {
                href: link,
                target: '_blank',
              },
              style: {
                color: '#3A84FF',
              },
            },
            that.$t('点击跳转到仓库查看')
          ),
        ]),
        theme: 'success',
      });
    },
    submitCodeReset() {
      this.submitCode.loading = false;
      this.submitCode.isConfirm = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.footer-tools-box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 24px;
  background: #e1ecff;
  box-shadow: 0 -2px 4px 0 #00000014;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;

  .run-tip {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    transform: translateY(-100%);
  }

  i {
    font-size: 14px;
  }
  .paasng-stop-shape {
    font-size: 18px;
    transform: translateY(0px);
    color: #ea3636;
  }
  .paasng-refresh-line {
    color: #2dcb56;
  }
}
.ml8 {
  margin-left: 8px;
}
.sandbox-container {
  background: #f5f7fa;
  .fore {
    color: #313238;
  }
  .top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 52px;
    padding: 0 24px;
    .title {
      display: flex;
      align-items: center;
    }
    .back {
      cursor: pointer;
      color: #3a84ff;
      font-size: 16px;
      i {
        transform: translateY(0px);
        font-weight: 700;
      }
      span {
        font-size: 14px;
      }
    }
  }
  .sandbox-alert-cls /deep/ .bk-alert-wraper {
    height: 32px;
    align-items: center;
  }
  .sandbox-content {
    padding-top: 16px;
    .top-box {
      display: flex;
      margin: 0 24px 16px;
      /deep/ .bk-button {
        flex-shrink: 0;
        margin-right: 12px;
      }
      /deep/ .bk-alert {
        flex: 1;
      }
    }
    .sandbox-editor {
      height: calc(100vh - 192px);
      &.is-footer {
        height: calc(100vh - 236px);
      }
      margin: 0 24px;
      &.collapse {
        margin-right: 0;
        /deep/ .bk-resize-layout-aside {
          width: 0 !important;
        }
      }
      .sandbox-resize-layout {
        height: 100%;
        /deep/ .bk-resize-layout-main {
          margin-right: 24px;
        }
        /deep/ .bk-resize-layout-aside {
          border: none !important;
        }
      }
      .iframe-box {
        height: 100%;
        iframe#iframe-embed {
          width: 100%;
          height: 100%;
          /* resize seems to inherit in at least Firefox */
          -webkit-resize: none;
          -moz-resize: none;
          resize: none;
        }
      }
      .iframe-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        width: 100%;
        height: 100%;
        img {
          width: 220px;
        }
      }
      .right-tab-cls {
        flex-shrink: 0;
      }
    }
  }
}
.sandbox-destroy-cls {
  .custom {
    font-size: 14px;
    line-height: 24px;
    color: #63656e;
    padding-bottom: 16px;
    .content-icon {
      color: #ea3636;
      position: absolute;
      top: 22px;
    }
    .content-text {
      display: inline-block;
      margin-left: 20px;
    }
  }
}
</style>
