"use client";

import { useState } from "react";

const platforms = [
  { name: "macOS", meta: "Apple Silicon · Intel", icon: "⌘" },
  { name: "Windows", meta: "Windows 10 / 11", icon: "⊞" },
  { name: "Linux", meta: "AppImage · x64", icon: "◇" },
];

export default function Home() {
  const [notice, setNotice] = useState(false);

  const virtualDownload = () => {
    setNotice(true);
    window.setTimeout(() => setNotice(false), 3200);
  };

  return (
    <main>
      <header className="nav shell">
        <a className="brand" href="#top" aria-label="Deep Dig 首页">
          <span className="brand-mark"><i /><i /><i /></span>
          <span>DEEP DIG</span>
        </a>
        <nav aria-label="主导航">
          <a href="#features">能力</a>
          <a href="#workflow">工作方式</a>
          <a href="#privacy">隐私</a>
        </nav>
        <a className="nav-download" href="#download">下载客户端 <span>↘</span></a>
      </header>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><span /> 桌面端 AI 数据抽取工具</div>
          <h1>把材料论文，<br />变成<span>可用的数据。</span></h1>
          <p className="hero-lead">
            Deep Dig 面向材料科学论文，按你指定的属性批量提取样品、结构、工艺、测试条件与性能数据。
          </p>
          <div className="hero-actions">
            <button className="primary" onClick={virtualDownload}>免费下载 <span>↓</span></button>
            <a className="secondary" href="#features">看看能做什么 <span>→</span></a>
          </div>
          <div className="trust-row">
            <span><b>✓</b> PDF 留在本地解析</span>
            <span><b>✓</b> 支持批量任务</span>
            <span><b>✓</b> 导出结构化 Excel</span>
          </div>
        </div>

        <div className="hero-visual" aria-label="Deep Dig 抽取界面示意">
          <div className="orb orb-one" /><div className="orb orb-two" />
          <div className="app-window">
            <div className="window-bar">
              <div className="traffic"><i /><i /><i /></div>
              <span>titanium_alloy_paper.pdf</span>
              <em>本地文件</em>
            </div>
            <div className="workspace">
              <aside>
                <div className="side-title">文档</div>
                <div className="doc-line active"><span>01</span> 摘要</div>
                <div className="doc-line"><span>02</span> 实验方法</div>
                <div className="doc-line"><span>03</span> 测试结果</div>
                <div className="page-mini"><b>Ti-6Al-4V alloy</b><i /><i /><i /><i /></div>
              </aside>
              <section className="extract-panel">
                <div className="panel-head"><span>抽取结果</span><em>6 个字段</em></div>
                <div className="field"><label>材料名称</label><strong>Ti-6Al-4V</strong><b>98%</b></div>
                <div className="field"><label>处理温度</label><strong>950 °C</strong><b>96%</b></div>
                <div className="field"><label>保温时间</label><strong>2 h</strong><b>94%</b></div>
                <div className="field featured"><label>抗拉强度</label><strong>1085 MPa</strong><b>99%</b></div>
                <div className="field"><label>延伸率</label><strong>14.2%</strong><b>92%</b></div>
                <div className="export-mini">导出数据 <span>↗</span></div>
              </section>
            </div>
          </div>
          <div className="floating-chip chip-one"><span>✓</span><div><b>抽取完成</b><small>24 篇文献 · 3m 18s</small></div></div>
          <div className="floating-chip chip-two"><span>↗</span><div><b>已生成表格</b><small>142 行结构化数据</small></div></div>
        </div>
      </section>

      <section className="ticker" aria-label="材料数据抽取能力">
        <div>样品 <span>✦</span> 制备工艺 <span>✦</span> 结构表征 <span>✦</span> 测试条件 <span>✦</span> 性能数据 <span>✦</span> 原文依据</div>
      </section>

      <section className="section shell" id="features">
        <div className="section-heading">
          <div><span className="kicker">01 · 一条专注的抽取流程</span><h2>从材料样品，<br />一直关联到性能数据。</h2></div>
          <p>不需要写正则，也不必反复复制粘贴。指定要提取的材料属性，Deep Dig 会按样品组织结果。</p>
        </div>
        <div className="use-grid">
          <article className="use-card general">
            <div className="card-top"><span className="card-no">A</span><em>SAMPLE PROPERTIES</em></div>
            <div className="card-icon"><span>⌁</span><i /></div>
            <h3>样品级属性</h3>
            <p>抽取成分、制备参数、形貌、孔结构、表面化学与表征结果，并归属到正确样品。</p>
            <ul><li>按需定义属性名称</li><li>多个 PDF 批量处理</li><li>保留单位、方法与来源</li></ul>
            <div className="tag-row"><span>合成工艺</span><span>结构表征</span><span>孔隙性质</span></div>
          </article>
          <article className="use-card research">
            <div className="card-top"><span className="card-no">B</span><em>MEASUREMENT LINKING</em></div>
            <div className="card-icon molecule"><span>⌬</span><i /></div>
            <h3>测试条件与性能关联</h3>
            <p>把电解液、电流密度、扫描速率等测试条件与同一次实验中的性能结果绑定。</p>
            <ul><li>区分样品属性与测量记录</li><li>同一样品支持多组测试</li><li>结果按条件展开到表格</li></ul>
            <div className="tag-row"><span>测试条件</span><span>电化学性能</span><span>多次测量</span></div>
          </article>
        </div>
      </section>

      <section className="workflow-wrap" id="workflow">
        <div className="section shell">
          <div className="section-heading compact">
            <div><span className="kicker">02 · 从文件到数据</span><h2>三步，挖出资料里的价值。</h2></div>
            <span className="status-pill"><i /> 本地优先工作流</span>
          </div>
          <div className="steps">
            <article><span className="step-no">01</span><div className="step-symbol">＋</div><h3>放入文件</h3><p>拖入单个文件或整个文件夹。PDF 文本在你的电脑上完成解析。</p></article>
            <article><span className="step-no">02</span><div className="step-symbol">⌘</div><h3>定义字段</h3><p>从模板开始，或用自然语言描述你想抽取的内容和格式。</p></article>
            <article><span className="step-no">03</span><div className="step-symbol">↗</div><h3>查看并导出</h3><p>查看逐文档状态与来源信息，把完成的批次导出为 Excel 工作簿。</p></article>
          </div>
        </div>
      </section>

      <section className="privacy section shell" id="privacy">
        <div className="privacy-copy">
          <span className="kicker">03 · 你的资料，不该失控</span>
          <h2>文件留在本地。<br />只有必要文本参与处理。</h2>
          <p>Deep Dig 是桌面优先的抽取工具。原始 PDF 不上传；文本先在本地解析，再按任务需要发送，默认不长期保存原文。</p>
          <div className="privacy-points"><span><b>01</b> 文件本地解析</span><span><b>02</b> 最少数据传输</span><span><b>03</b> 结果可追溯</span></div>
        </div>
        <div className="shield-card">
          <div className="shield"><span>•</span></div>
          <div className="data-line"><span>原始 PDF</span><b>留在设备</b></div>
          <div className="data-line"><span>必要文本</span><b>加密传输</b></div>
          <div className="data-line"><span>抽取结果</span><b>由你保存</b></div>
        </div>
      </section>

      <section className="download-section" id="download">
        <div className="shell download-inner">
          <span className="kicker">现在开始深挖</span>
          <h2>少一点复制粘贴，<br />多一点真正的发现。</h2>
          <p>Deep Dig 内测版即将开放。选择你的平台，抢先体验桌面端。</p>
          <div className="platforms">
            {platforms.map((p) => <button key={p.name} onClick={virtualDownload}><span className="platform-icon">{p.icon}</span><span><small>下载适用于</small><b>{p.name}</b><em>{p.meta}</em></span><i>↓</i></button>)}
          </div>
          <small className="release-note">当前为产品预览，下载包暂未正式提供 · v0.1 Preview</small>
        </div>
      </section>

      <footer className="shell">
        <a className="brand" href="#top"><span className="brand-mark"><i /><i /><i /></span><span>DEEP DIG</span></a>
        <p>让散落在资料里的信息，成为可以继续工作的数据。</p>
        <span>© 2026 Deep Dig</span>
      </footer>

      <div className={`toast ${notice ? "show" : ""}`} role="status" aria-live="polite">
        <span>◷</span><div><b>下载包正在准备中</b><small>这是虚拟下载入口，内测开放后即可获取。</small></div>
      </div>
    </main>
  );
}
