import {
  ArrowDownRight,
  ArrowRight,
  Atom,
  Blocks,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  Dna,
  Download,
  FileSearch,
  FileText,
  FlaskConical,
  Gauge,
  Layers3,
  Microscope,
  MoveRight,
  Network,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Table2,
  Zap,
} from 'lucide-react';

const extractionRows = [
  ['Ti-6Al-4V', '980 MPa', '14.2%', 'Laser PBF'],
  ['AlSi10Mg', '340 MPa', '5.8%', 'SLM'],
  ['IN718', '1,180 MPa', '20.1%', 'DED'],
];

const domains = [
  {
    number: '01',
    icon: FlaskConical,
    title: '材料科学',
    caption: 'Materials',
    description: '从论文中批量提取材料成分、制备工艺、实验条件与性能参数。',
    fields: ['化学成分', '热处理制度', '力学性能'],
  },
  {
    number: '02',
    icon: Dna,
    title: '生命科学',
    caption: 'Life Science',
    description: '整理研究对象、样本量、干预方式、指标与统计结论。',
    fields: ['样本规模', '实验组别', '关键指标'],
  },
  {
    number: '03',
    icon: Network,
    title: '产业研究',
    caption: 'Industry',
    description: '把报告中的企业、产品、产能、价格与市场数据汇总成表。',
    fields: ['公司名称', '产能规模', '市场份额'],
  },
  {
    number: '04',
    icon: Atom,
    title: '通用文献',
    caption: 'General',
    description: '不受固定模板限制，用自然语言定义任何需要抽取的字段。',
    fields: ['研究方法', '核心结论', '自定义字段'],
  },
];

export function App() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Deep Dig 首页">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>Deep Dig</span>
        </a>
        <nav className="nav-links" aria-label="主导航">
          <a href="#capabilities">产品能力</a>
          <a href="#examples">领域示例</a>
          <a href="#how-it-works">工作方式</a>
        </nav>
        <a className="nav-cta" href="#download">
          获取客户端
          <ArrowDownRight size={17} strokeWidth={2.4} />
        </a>
      </header>

      <section className="hero section-grid" id="top">
        <div className="hero-copy">
          <div className="availability reveal reveal-1">
            <span className="pulse" />
            公测期间 · 免费 50 次提取
          </div>
          <h1 className="reveal reveal-2">
            从文献到<br />数据，<br />
            <span>只需片刻。</span>
          </h1>
          <p className="hero-lede reveal reveal-3">
            指定你关心的字段，Deep Dig 自动从 PDF、研究文稿与报告中定位信息，输出干净、可计算的表格数据。
          </p>
          <div className="hero-actions reveal reveal-4">
            <a className="button button-primary" href="#download">
              免费开始使用
              <ArrowRight size={19} />
            </a>
            <a className="text-link" href="#extraction-demo">
              查看提取示例
              <MoveRight size={18} />
            </a>
          </div>
          <div className="trust-row reveal reveal-4">
            <span><Zap size={15} />高速批处理</span>
            <span><ShieldCheck size={15} />本地解析</span>
            <span><Table2 size={15} />一键导出表格</span>
          </div>
        </div>

        <div className="hero-visual reveal reveal-3" id="extraction-demo" aria-label="文献字段提取演示">
          <div className="window-bar">
            <div className="traffic-lights"><i /><i /><i /></div>
            <span>DEEP DIG / EXTRACTION 001</span>
            <span className="window-status"><i /> RUNNING</span>
          </div>
          <div className="extraction-stage">
            <article className="source-document">
              <div className="document-meta">
                <FileText size={17} />
                <span>alloy_review_2025.pdf</span>
                <small>18 pages</small>
              </div>
              <div className="paper-lines">
                <span className="line line-wide" />
                <span className="line line-medium" />
                <span className="line line-short" />
                <p>
                  The <mark>Ti-6Al-4V</mark> specimens produced by <mark>Laser PBF</mark>
                  exhibited a tensile strength of <mark>980 MPa</mark> and elongation of <mark>14.2%</mark>.
                </p>
                <span className="line line-wide" />
                <span className="line line-medium" />
                <div className="scan-line" />
              </div>
              <span className="document-page">04 / 18</span>
            </article>

            <div className="process-rail">
              <span>识别</span>
              <div><ScanSearch size={19} /></div>
              <i />
              <span>对齐</span>
              <div><Blocks size={19} /></div>
            </div>

            <article className="result-sheet">
              <div className="sheet-heading">
                <div>
                  <span>STRUCTURED OUTPUT</span>
                  <strong>3 条数据已提取</strong>
                </div>
                <span className="xlsx-badge">.XLSX</span>
              </div>
              <div className="data-table">
                <div className="table-row table-head">
                  <span>材料</span><span>抗拉强度</span><span>延伸率</span><span>工艺</span>
                </div>
                {extractionRows.map((row, index) => (
                  <div className="table-row" key={row[0]}>
                    {row.map((cell) => <span key={cell}>{cell}</span>)}
                    <i style={{ animationDelay: `${1.4 + index * 0.35}s` }} />
                  </div>
                ))}
              </div>
              <div className="sheet-footer">
                <span><Check size={14} />字段校验完成</span>
                <span>00:08.42</span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <div className="signal-strip" aria-hidden="true">
        <div>
          <span>PDF</span><ChevronRight /><span>定位</span><ChevronRight /><span>提取</span><ChevronRight /><span>校验</span><ChevronRight /><span>XLSX / CSV</span>
          <span>PDF</span><ChevronRight /><span>定位</span><ChevronRight /><span>提取</span><ChevronRight /><span>校验</span><ChevronRight /><span>XLSX / CSV</span>
        </div>
      </div>

      <section className="capabilities section-grid" id="capabilities">
        <div className="section-intro">
          <span className="section-index">01 / CAPABILITIES</span>
          <h2>不只读懂文献，<br />更把知识变成数据。</h2>
          <p>同一套高速提取引擎，兼顾开放场景与专业材料文献。</p>
        </div>

        <div className="capability-composition">
          <article className="capability capability-general">
            <div className="capability-number">A</div>
            <Sparkles size={24} />
            <span className="capability-tag">GENERAL EXTRACTION</span>
            <h3>通用字段提取</h3>
            <p>直接描述你想要的数据，无需预设模板。适合论文、报告、档案及各类长文稿。</p>
            <ul>
              <li><Check />自然语言定义字段</li>
              <li><Check />跨文档统一数据结构</li>
              <li><Check />结果附带来源定位</li>
            </ul>
          </article>

          <article className="capability capability-materials">
            <div className="capability-number">B</div>
            <Microscope size={24} />
            <span className="capability-tag">MATERIALS INTELLIGENCE</span>
            <h3>材料文献提取</h3>
            <p>为复杂材料体系优化，识别样品、工艺、测试条件、单位与性能之间的对应关系。</p>
            <div className="material-map">
              <span>样品</span><i /><span>工艺</span><i /><span>性能</span>
            </div>
            <ul>
              <li><Check />多样品关系对齐</li>
              <li><Check />单位与条件保留</li>
              <li><Check />适配材料数据建模</li>
            </ul>
          </article>

          <aside className="quota-block">
            <div><Gauge size={23} /><span>PUBLIC BETA</span></div>
            <strong>50</strong>
            <p>次免费提取额度</p>
            <small>无需信用卡 · 公测期开放</small>
          </aside>
        </div>
      </section>

      <section className="workflow section-grid" id="how-it-works">
        <div className="workflow-title">
          <span className="section-index">02 / HOW IT WORKS</span>
          <h2>三步，把资料库<br />变成数据集。</h2>
        </div>
        <ol className="workflow-steps">
          <li>
            <span className="step-number">01</span>
            <div className="step-icon"><Layers3 /></div>
            <h3>导入文稿</h3>
            <p>批量选择 PDF 等研究文稿，保留原始文件与解析内容。</p>
            <span className="step-meta">PDF · DOCUMENTS</span>
          </li>
          <li>
            <span className="step-number">02</span>
            <div className="step-icon"><FileSearch /></div>
            <h3>指定字段</h3>
            <p>输入材料牌号、实验条件、关键指标，或任何你需要的字段。</p>
            <span className="step-meta">PROMPT · SCHEMA</span>
          </li>
          <li>
            <span className="step-number">03</span>
            <div className="step-icon"><Database /></div>
            <h3>获得表格</h3>
            <p>结构化结果可直接导出，用于统计分析、可视化与机器学习建模。</p>
            <span className="step-meta">XLSX · CSV · DATA</span>
          </li>
        </ol>
      </section>

      <section className="examples section-grid" id="examples">
        <div className="examples-heading">
          <div>
            <span className="section-index">03 / USE CASES</span>
            <h2>一个工具，<br />深入不同领域。</h2>
          </div>
          <p>字段由你定义，结构由 Deep Dig 整理。<br />从单篇验证，到数百篇批量研究。</p>
        </div>
        <div className="domain-list">
          {domains.map(({ number, icon: Icon, title, caption, description, fields }) => (
            <article className="domain-row" key={number}>
              <span className="domain-number">{number}</span>
              <div className="domain-icon"><Icon /></div>
              <div className="domain-title"><h3>{title}</h3><span>{caption}</span></div>
              <p>{description}</p>
              <div className="field-list">{fields.map((field) => <span key={field}>{field}</span>)}</div>
              <ArrowDownRight className="domain-arrow" />
            </article>
          ))}
        </div>
      </section>

      <section className="download section-grid" id="download">
        <div className="download-copy">
          <span className="section-index light">04 / DESKTOP APP</span>
          <h2>在你的电脑上，<br />开始深挖。</h2>
          <p>Deep Dig 桌面客户端正在准备中。首个版本将支持 macOS 与 Windows。</p>
          <div className="download-note"><CircleDot size={15} />下载开放后，我们会在这里第一时间更新。</div>
        </div>
        <div className="download-options">
          <button type="button" className="download-card" aria-disabled="true" title="macOS 客户端即将上线">
            <span className="os-symbol">⌘</span>
            <span><small>DOWNLOAD FOR</small><strong>macOS</strong></span>
            <em>即将上线</em>
            <Download />
          </button>
          <button type="button" className="download-card" aria-disabled="true" title="Windows 客户端即将上线">
            <span className="windows-symbol"><i /><i /><i /><i /></span>
            <span><small>DOWNLOAD FOR</small><strong>Windows</strong></span>
            <em>即将上线</em>
            <Download />
          </button>
        </div>
      </section>

      <footer className="site-footer">
        <div className="brand footer-brand">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>Deep Dig</span>
        </div>
        <p>Extract less. Discover more.</p>
        <span>© 2026 DEEP DIG</span>
      </footer>
    </main>
  );
}
