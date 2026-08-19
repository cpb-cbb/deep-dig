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
import { useEffect, useState } from 'react';

type Language = 'zh' | 'en';

const extractionRows = [
  ['Ti-6Al-4V', '980 MPa', '14.2%', 'Laser PBF'],
  ['AlSi10Mg', '340 MPa', '5.8%', 'SLM'],
  ['IN718', '1,180 MPa', '20.1%', 'DED'],
];

const domainIcons = [FlaskConical, Dna, Network, Atom];

const translations = {
  zh: {
    documentTitle: 'Deep Dig — 从文献到数据，只需片刻',
    homeLabel: 'Deep Dig 首页',
    navLabel: '主导航',
    nav: ['产品能力', '领域示例', '工作方式'],
    client: '获取客户端',
    languageLabel: '切换为英文',
    languageShort: 'EN',
    availability: '开源自部署 · 无内置任务额度',
    heroTitle: ['从文献到', '数据，', '只需片刻。'],
    heroLede: '指定你关心的字段，Deep Dig 自动从 PDF、研究文稿与报告中定位信息，输出干净、可计算的表格数据。',
    start: '免费开始使用',
    viewExample: '查看提取示例',
    trust: ['高速批处理', '本地解析', '一键导出表格'],
    demoLabel: '文献字段提取演示',
    pages: '18 页',
    identify: '识别',
    align: '对齐',
    extracted: '3 条数据已提取',
    tableHead: ['材料', '抗拉强度', '延伸率', '工艺'],
    validated: '字段校验完成',
    signal: ['PDF', '定位', '提取', '校验', 'XLSX / CSV'],
    capabilitiesTitle: ['不只读懂文献，', '更把知识变成数据。'],
    capabilitiesLede: '同一套版本化工作流引擎，支持专业模板、自定义字段与实体关系。',
    general: {
      title: '通用字段提取',
      description: '通过字段构建器定义名称、类型和抽取说明，适合论文、合同、报告、档案及各类长文稿。',
      benefits: ['类型化字段 Schema', '跨文档统一数据结构', '结果附带来源依据'],
    },
    materials: {
      title: '材料文献提取',
      description: '为复杂材料体系优化，识别样品、工艺、测试条件、单位与性能之间的对应关系。',
      map: ['样品', '工艺', '性能'],
      benefits: ['多样品关系对齐', '单位与条件保留', '适配材料数据建模'],
    },
    openSource: '无内置提取额度',
    openSourceNote: '运行成本取决于你选择的模型服务商',
    workflowTitle: ['三步，把资料库', '变成数据集。'],
    workflowIntro: '以下用 12 篇钛合金论文，演示“字段”到底是什么。',
    workflowSteps: [
      {
        title: '导入文稿',
        description: '批量选择 PDF 等研究文稿，保留原始文件与解析内容。',
        meta: 'PDF · DOCUMENTS',
        exampleLabel: '示例输入',
        exampleValue: '12 篇钛合金论文',
        exampleTags: ['alloy_review.pdf', 'lpbf_study.pdf', '+ 10'],
      },
      {
        title: '指定字段',
        description: '“字段”就是你希望每篇文献都回答的问题，也就是最终表格的列名。',
        meta: 'PROMPT · SCHEMA',
        exampleLabel: '希望提取',
        exampleValue: '每个样品的关键数据',
        exampleTags: ['材料牌号', '制备工艺', '抗拉强度', '延伸率'],
      },
      {
        title: '获得表格',
        description: 'Deep Dig 逐篇定位答案并对齐到同一行，可直接用于分析、可视化与建模。',
        meta: 'XLSX · CSV · DATA',
        exampleLabel: '示例输出 · 第 1 行',
        exampleValue: 'Ti-6Al-4V',
        exampleTags: ['Laser PBF', '980 MPa', '14.2%'],
      },
    ],
    examplesTitle: ['一个工具，', '深入不同领域。'],
    examplesLede: ['字段由你定义，结构由 Deep Dig 整理。', '从单篇验证，到数百篇批量研究。'],
    domains: [
      { title: '材料科学', caption: 'Materials', description: '从论文中批量提取材料成分、制备工艺、实验条件与性能参数。', fields: ['化学成分', '热处理制度', '力学性能'] },
      { title: '法律文档', caption: 'Legal', description: '用自定义字段整理合同主体、日期、义务、期限和条款依据。', fields: ['合同主体', '生效日期', '关键义务'] },
      { title: '医学研究', caption: 'Medical', description: '整理研究对象、样本量、干预方式、指标与统计结论。', fields: ['样本规模', '干预方式', '关键指标'] },
      { title: '实体关系', caption: 'Knowledge Graph', description: '按指定类型识别人名、机构、药物、法规及其显式关系。', fields: ['实体类型', '关系类型', '来源证据'] },
    ],
    downloadTitle: ['在你的电脑上，', '开始深挖。'],
    downloadLede: 'Deep Dig 桌面客户端正在准备中。首个版本将支持 macOS 与 Windows。',
    downloadNote: '下载开放后，我们会在这里第一时间更新。',
    contact: '联系我们',
    comingSoon: '即将上线',
    macTitle: 'macOS 客户端即将上线',
    windowsTitle: 'Windows 客户端即将上线',
  },
  en: {
    documentTitle: 'Deep Dig — From papers to data, in moments',
    homeLabel: 'Deep Dig home',
    navLabel: 'Main navigation',
    nav: ['Capabilities', 'Use cases', 'How it works'],
    client: 'Get the app',
    languageLabel: 'Switch to Chinese',
    languageShort: '中',
    availability: 'OPEN SOURCE · SELF-HOSTED',
    heroTitle: ['From papers', 'to data,', 'in moments.'],
    heroLede: 'Tell Deep Dig which fields matter. It finds them across PDFs, research papers, and reports, then returns clean, analysis-ready tables.',
    start: 'Start for free',
    viewExample: 'See an extraction',
    trust: ['High-speed batches', 'Local parsing', 'One-click exports'],
    demoLabel: 'Document field extraction demo',
    pages: '18 pages',
    identify: 'FIND',
    align: 'ALIGN',
    extracted: '3 records extracted',
    tableHead: ['Material', 'Strength', 'Elong.', 'Process'],
    validated: 'Fields validated',
    signal: ['PDF', 'LOCATE', 'EXTRACT', 'VALIDATE', 'XLSX / CSV'],
    capabilitiesTitle: ['More than reading papers.', 'Knowledge becomes data.'],
    capabilitiesLede: 'One versioned workflow engine for specialist templates, custom fields, and entity relationships.',
    general: {
      title: 'General extraction',
      description: 'Use the field builder to define names, types, and extraction guidance for papers, contracts, reports, archives, and long documents.',
      benefits: ['Typed field schemas', 'One schema across documents', 'Every result links to evidence'],
    },
    materials: {
      title: 'Materials extraction',
      description: 'Purpose-built for complex materials research, connecting samples, processing, test conditions, units, and properties.',
      map: ['SAMPLE', 'PROCESS', 'PROPERTY'],
      benefits: ['Align multi-sample relationships', 'Preserve units and conditions', 'Ready for materials modeling'],
    },
    openSource: 'no built-in extraction quota',
    openSourceNote: 'Usage cost depends on your LLM provider',
    workflowTitle: ['Three steps from', 'library to dataset.'],
    workflowIntro: 'Here is what “fields” mean, using 12 titanium-alloy papers as one continuous example.',
    workflowSteps: [
      {
        title: 'Import documents',
        description: 'Select PDFs and research documents in batches while keeping the source and parsed content together.',
        meta: 'PDF · DOCUMENTS',
        exampleLabel: 'EXAMPLE INPUT',
        exampleValue: '12 titanium-alloy papers',
        exampleTags: ['alloy_review.pdf', 'lpbf_study.pdf', '+ 10'],
      },
      {
        title: 'Define fields',
        description: 'A “field” is simply a question every paper should answer—and a column in your final table.',
        meta: 'PROMPT · SCHEMA',
        exampleLabel: 'FIELDS TO EXTRACT',
        exampleValue: 'Key data for every sample',
        exampleTags: ['Alloy', 'Process', 'Tensile strength', 'Elongation'],
      },
      {
        title: 'Get your table',
        description: 'Deep Dig locates each answer and aligns it into rows, ready for analysis, visualization, and modeling.',
        meta: 'XLSX · CSV · DATA',
        exampleLabel: 'EXAMPLE OUTPUT · ROW 1',
        exampleValue: 'Ti-6Al-4V',
        exampleTags: ['Laser PBF', '980 MPa', '14.2%'],
      },
    ],
    examplesTitle: ['One tool.', 'Many deep domains.'],
    examplesLede: ['You define the fields. Deep Dig creates the structure.', 'From one-paper validation to studies with hundreds.'],
    domains: [
      { title: 'Materials science', caption: 'Materials', description: 'Extract compositions, processes, experimental conditions, and properties across papers.', fields: ['Composition', 'Heat treatment', 'Properties'] },
      { title: 'Legal documents', caption: 'Legal', description: 'Structure contract parties, dates, obligations, deadlines, and supporting clauses.', fields: ['Parties', 'Effective date', 'Obligations'] },
      { title: 'Medical research', caption: 'Medical', description: 'Organize cohorts, sample sizes, interventions, outcomes, and statistical findings.', fields: ['Sample size', 'Intervention', 'Outcomes'] },
      { title: 'Entity graphs', caption: 'Knowledge Graph', description: 'Find typed people, organizations, drugs, statutes, and their explicit relationships.', fields: ['Entity types', 'Relations', 'Evidence'] },
    ],
    downloadTitle: ['Dig deeper,', 'right on your desktop.'],
    downloadLede: 'The Deep Dig desktop app is on its way. The first release will support macOS and Windows.',
    downloadNote: 'Download links will appear here as soon as the apps are ready.',
    contact: 'Contact',
    comingSoon: 'Coming soon',
    macTitle: 'Deep Dig for macOS is coming soon',
    windowsTitle: 'Deep Dig for Windows is coming soon',
  },
} as const;

export function App() {
  const [language, setLanguage] = useState<Language>(() => (
    window.localStorage.getItem('deep-dig-language') === 'en' ? 'en' : 'zh'
  ));
  const t = translations[language];

  useEffect(() => {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.title = t.documentTitle;
    window.localStorage.setItem('deep-dig-language', language);
  }, [language, t.documentTitle]);

  function toggleLanguage() {
    setLanguage((current) => current === 'zh' ? 'en' : 'zh');
  }

  return (
    <main className={`site-main lang-${language}`}>
      <header className="site-header">
        <a className="brand" href="#top" aria-label={t.homeLabel}>
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>Deep Dig</span>
        </a>
        <nav className="nav-links" aria-label={t.navLabel}>
          <a href="#capabilities">{t.nav[0]}</a>
          <a href="#examples">{t.nav[1]}</a>
          <a href="#how-it-works">{t.nav[2]}</a>
        </nav>
        <div className="header-actions">
          <button className="language-toggle" type="button" onClick={toggleLanguage} aria-label={t.languageLabel}>
            <span className={language === 'zh' ? 'active' : ''}>中</span>
            <i />
            <span className={language === 'en' ? 'active' : ''}>EN</span>
          </button>
          <a className="nav-cta" href="#download">
            {t.client}
            <ArrowDownRight size={17} strokeWidth={2.4} />
          </a>
        </div>
      </header>

      <section className="hero section-grid" id="top">
        <div className="hero-copy">
          <div className="availability reveal reveal-1"><span className="pulse" />{t.availability}</div>
          <h1 className="reveal reveal-2">
            {t.heroTitle[0]}<br />{t.heroTitle[1]}<br />
            <span>{t.heroTitle[2]}</span>
          </h1>
          <p className="hero-lede reveal reveal-3">{t.heroLede}</p>
          <div className="hero-actions reveal reveal-4">
            <a className="button button-primary" href="#download">{t.start}<ArrowRight size={19} /></a>
            <a className="text-link" href="#extraction-demo">{t.viewExample}<MoveRight size={18} /></a>
          </div>
          <div className="trust-row reveal reveal-4">
            <span><Zap size={15} />{t.trust[0]}</span>
            <span><ShieldCheck size={15} />{t.trust[1]}</span>
            <span><Table2 size={15} />{t.trust[2]}</span>
          </div>
        </div>

        <div className="hero-visual reveal reveal-3" id="extraction-demo" aria-label={t.demoLabel}>
          <div className="window-bar">
            <div className="traffic-lights"><i /><i /><i /></div>
            <span>DEEP DIG / EXTRACTION 001</span>
            <span className="window-status"><i /> RUNNING</span>
          </div>
          <div className="extraction-stage">
            <article className="source-document">
              <div className="document-meta"><FileText size={17} /><span>alloy_review_2025.pdf</span><small>{t.pages}</small></div>
              <div className="paper-lines">
                <span className="line line-wide" /><span className="line line-medium" /><span className="line line-short" />
                <p>The <mark>Ti-6Al-4V</mark> specimens produced by <mark>Laser PBF</mark> exhibited a tensile strength of <mark>980 MPa</mark> and elongation of <mark>14.2%</mark>.</p>
                <span className="line line-wide" /><span className="line line-medium" /><div className="scan-line" />
              </div>
              <span className="document-page">04 / 18</span>
            </article>

            <div className="process-rail">
              <span>{t.identify}</span><div><ScanSearch size={19} /></div><i /><span>{t.align}</span><div><Blocks size={19} /></div>
            </div>

            <article className="result-sheet">
              <div className="sheet-heading">
                <div><span>STRUCTURED OUTPUT</span><strong>{t.extracted}</strong></div>
                <span className="xlsx-badge">.XLSX</span>
              </div>
              <div className="data-table">
                <div className="table-row table-head">{t.tableHead.map((heading) => <span key={heading}>{heading}</span>)}</div>
                {extractionRows.map((row, index) => (
                  <div className="table-row" key={row[0]}>
                    {row.map((cell) => <span key={cell}>{cell}</span>)}
                    <i style={{ animationDelay: `${1.4 + index * 0.35}s` }} />
                  </div>
                ))}
              </div>
              <div className="sheet-footer"><span><Check size={14} />{t.validated}</span><span>00:08.42</span></div>
            </article>
          </div>
        </div>
      </section>

      <div className="signal-strip" aria-hidden="true">
        <div>
          {[...t.signal, ...t.signal].map((item, index) => (
            <span className="signal-item" key={`${item}-${index}`}>{item}{index < t.signal.length * 2 - 1 && <ChevronRight />}</span>
          ))}
        </div>
      </div>

      <section className="capabilities section-grid" id="capabilities">
        <div className="section-intro">
          <span className="section-index">01 / CAPABILITIES</span>
          <h2>{t.capabilitiesTitle[0]}<br />{t.capabilitiesTitle[1]}</h2>
          <p>{t.capabilitiesLede}</p>
        </div>

        <div className="capability-composition">
          <article className="capability capability-general">
            <div className="capability-number">A</div><Sparkles size={24} />
            <span className="capability-tag">GENERAL EXTRACTION</span><h3>{t.general.title}</h3><p>{t.general.description}</p>
            <ul>{t.general.benefits.map((benefit) => <li key={benefit}><Check />{benefit}</li>)}</ul>
          </article>

          <article className="capability capability-materials">
            <div className="capability-number">B</div><Microscope size={24} />
            <span className="capability-tag">MATERIALS INTELLIGENCE</span><h3>{t.materials.title}</h3><p>{t.materials.description}</p>
            <div className="material-map"><span>{t.materials.map[0]}</span><i /><span>{t.materials.map[1]}</span><i /><span>{t.materials.map[2]}</span></div>
            <ul>{t.materials.benefits.map((benefit) => <li key={benefit}><Check />{benefit}</li>)}</ul>
          </article>

          <aside className="open-source-block">
            <div><Gauge size={23} /><span>OPEN SOURCE</span></div><strong>∞</strong><p>{t.openSource}</p><small>{t.openSourceNote}</small>
          </aside>
        </div>
      </section>

      <section className="workflow section-grid" id="how-it-works">
        <div className="workflow-title">
          <span className="section-index">02 / HOW IT WORKS</span>
          <h2>{t.workflowTitle[0]}<br />{t.workflowTitle[1]}</h2>
          <p className="workflow-intro">{t.workflowIntro}</p>
        </div>
        <ol className="workflow-steps">
          {t.workflowSteps.map((step, index) => {
            const StepIcon = [Layers3, FileSearch, Database][index];
            return (
              <li key={step.title}>
                <span className="step-number">0{index + 1}</span>
                <div className="step-icon"><StepIcon /></div>
                <h3>{step.title}</h3><p>{step.description}</p>
                <div className={`step-example step-example-${index + 1}`}>
                  <span>{step.exampleLabel}</span><strong>{step.exampleValue}</strong>
                  <div>{step.exampleTags.map((tag) => <em key={tag}>{tag}</em>)}</div>
                </div>
                <span className="step-meta">{step.meta}</span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="examples section-grid" id="examples">
        <div className="examples-heading">
          <div><span className="section-index">03 / USE CASES</span><h2>{t.examplesTitle[0]}<br />{t.examplesTitle[1]}</h2></div>
          <p>{t.examplesLede[0]}<br />{t.examplesLede[1]}</p>
        </div>
        <div className="domain-list">
          {t.domains.map(({ title, caption, description, fields }, index) => {
            const Icon = domainIcons[index];
            return (
              <article className="domain-row" key={caption}>
                <span className="domain-number">0{index + 1}</span><div className="domain-icon"><Icon /></div>
                <div className="domain-title"><h3>{title}</h3><span>{caption}</span></div><p>{description}</p>
                <div className="field-list">{fields.map((field) => <span key={field}>{field}</span>)}</div><ArrowDownRight className="domain-arrow" />
              </article>
            );
          })}
        </div>
      </section>

      <section className="download section-grid" id="download">
        <div className="download-copy">
          <span className="section-index light">04 / DESKTOP APP</span><h2>{t.downloadTitle[0]}<br />{t.downloadTitle[1]}</h2>
          <p>{t.downloadLede}</p><div className="download-note"><CircleDot size={15} />{t.downloadNote}</div>
        </div>
        <div className="download-options">
          <button type="button" className="download-card" aria-disabled="true" title={t.macTitle}>
            <span className="os-symbol">⌘</span><span><small>DOWNLOAD FOR</small><strong>macOS</strong></span><em>{t.comingSoon}</em><Download />
          </button>
          <button type="button" className="download-card" aria-disabled="true" title={t.windowsTitle}>
            <span className="windows-symbol"><i /><i /><i /><i /></span><span><small>DOWNLOAD FOR</small><strong>Windows</strong></span><em>{t.comingSoon}</em><Download />
          </button>
        </div>
      </section>

      <footer className="site-footer">
        <div className="brand footer-brand"><span className="brand-mark" aria-hidden="true"><span /></span><span>Deep Dig</span></div>
        <div className="footer-center">
          <p>Extract less. Discover more.</p>
          <a className="footer-contact" href="mailto:cbb4611@gmail.com">
            <span>{t.contact}</span>
            cbb4611@gmail.com
          </a>
        </div>
        <span>© 2026 DEEP DIG</span>
      </footer>
    </main>
  );
}
