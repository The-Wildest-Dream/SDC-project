import { useState, type CSSProperties } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';

const EASE = [0.22, 1, 0.36, 1] as const;
const snap = { type: 'spring', stiffness: 280, damping: 22 } as const;

function SceneNumber({ n, label }: { n: string; label: string }) {
  return (
    <div className="scene-number">
      <span>{n}</span><i />{label}
    </div>
  );
}

function Rule({ className = '' }: { className?: string }) {
  return <span className={`hairline ${className}`} aria-hidden="true" />;
}

function PaperLine({ width, delay = 0 }: { width: string; delay?: number }) {
  return (
    <motion.span
      className="paper-line"
      initial={{ scaleX: 0, opacity: 0 }}
      animate={{ scaleX: 1, opacity: 1 }}
      transition={{ duration: 0.7, delay, ease: EASE }}
      style={{ width, transformOrigin: 'left' }}
    />
  );
}

export function Scene01() {
  const [phase, setPhase] = useState(0);
  useSceneTimer([
    { time: 500, callback: () => setPhase(1) },
    { time: 1200, callback: () => setPhase(2) },
    { time: 2150, callback: () => setPhase(3) },
    { time: 3250, callback: () => setPhase(4) },
    { time: 4450, callback: () => setPhase(5) },
  ]);

  return (
    <motion.section
      className="film-scene opening-scene"
      initial={{ opacity: 0, clipPath: 'inset(0 0 0 100%)' }}
      animate={{ opacity: 1, clipPath: 'inset(0 0 0 0%)' }}
      exit={{ opacity: 0, scale: 1.045, filter: 'blur(7px)', transition: { duration: 0.32 } }}
      transition={{ duration: 0.56, ease: EASE }}
    >
      <div className="opening-grid" />
      <SceneNumber n="01" label="THE QUOTE FOLIO" />
      <div className="opening-copy">
        <motion.div
          className="red-register"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ ...snap, delay: 0.06 }}
        />
        <h1 className="headline opening-headline">
          <span>报价</span>
          <span>不该靠</span>
          <span className="accent-word">拼凑。</span>
        </h1>
        <motion.p
          className="eyebrow opening-sub"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: phase >= 2 ? 1 : 0, y: phase >= 2 ? 0 : 18 }}
          transition={{ duration: 0.42, ease: EASE }}
        >
          成本 · 历史 · 账期 · 审批
        </motion.p>
      </div>

      <div className="paper-workspace">
        {[
          { label: 'COST INPUTS', detail: '材料 / 人工 / 制造费用', top: '4%', left: '6%', rotate: -8, delay: 0.13, w: '72%' },
          { label: 'TRANSACTION LOG', detail: '可比历史价格', top: '34%', left: '16%', rotate: 5, delay: 0.52, w: '61%' },
          { label: 'PAYMENT TERMS', detail: '账期与资金成本', top: '62%', left: '4%', rotate: -3, delay: 0.92, w: '68%' },
        ].map((slip, i) => (
          <motion.div
            key={slip.label}
            className={`input-slip slip-${i + 1}`}
            initial={{ opacity: 0, y: 64, rotate: slip.rotate + 11, scale: 0.88 }}
            animate={{
              opacity: phase >= i ? 1 : 0,
              y: phase >= i ? 0 : 64,
              rotate: phase >= 4 ? 0 : slip.rotate,
              scale: phase >= i ? 1 : 0.88,
            }}
            transition={{ ...snap, delay: slip.delay }}
            style={{ top: slip.top, left: slip.left, width: slip.w, zIndex: i + 1 }}
          >
            <div className="slip-top"><span>{slip.label}</span><span>— 0{i + 1}</span></div>
            <div className="slip-detail">{slip.detail}</div>
            <div className="slip-lines"><PaperLine width="64%" delay={slip.delay + 0.12} /><PaperLine width="89%" delay={slip.delay + 0.23} /></div>
            <span className="slip-corner" />
          </motion.div>
        ))}
        <motion.div
          className="folio-edge"
          initial={{ scaleY: 0 }}
          animate={{ scaleY: phase >= 4 ? 1 : 0 }}
          transition={{ duration: 0.5, ease: EASE }}
        />
        <motion.div
          className="opening-registration"
          animate={{
            x: phase >= 5 ? -52 : 0,
            y: phase >= 5 ? -18 : 0,
            scaleX: phase >= 5 ? 1.7 : 1,
          }}
          transition={{ duration: 0.48, ease: EASE }}
        />
      </div>
      <motion.div
        className="demo-mark"
        initial={{ opacity: 0 }}
        animate={{ opacity: phase >= 3 ? 1 : 0 }}
        transition={{ duration: 0.32 }}
      >
        模拟演示 / 合成数据
      </motion.div>
      <Rule className="opening-bottom-rule" />
      <motion.span className="opening-index" animate={{ opacity: phase >= 4 ? 0.72 : 0.34 }}>NAMLESS / QUOTATION ASSISTANT</motion.span>
    </motion.section>
  );
}

export function Scene02() {
  const [phase, setPhase] = useState(0);
  useSceneTimer([
    { time: 360, callback: () => setPhase(1) },
    { time: 1250, callback: () => setPhase(2) },
    { time: 2200, callback: () => setPhase(3) },
    { time: 3350, callback: () => setPhase(4) },
    { time: 4180, callback: () => setPhase(5) },
  ]);
  const costs = [
    { name: '材料', index: '01', width: '82%' },
    { name: '人工', index: '02', width: '64%' },
    { name: '制造费用', index: '03', width: '73%' },
    { name: '批次 + 物流', index: '04', width: '48%' },
  ];
  return (
    <motion.section
      className="film-scene costing-scene"
      initial={{ opacity: 0, scale: 1.07, clipPath: 'polygon(0 0,100% 0,100% 0,0 0)' }}
      animate={{ opacity: 1, scale: 1, clipPath: 'polygon(0 0,100% 0,100% 100%,0 100%)' }}
      exit={{ opacity: 0, scale: 1.04, filter: 'blur(6px)', transition: { duration: 0.3 } }}
      transition={{ duration: 0.62, ease: EASE }}
    >
      <div className="ledger-margin" />
      <SceneNumber n="02" label="COST SNAPSHOT" />
      <motion.h2 className="headline ledger-headline" initial={{ opacity: 0, x: -60 }} animate={{ opacity: phase >= 1 ? 1 : 0, x: phase >= 1 ? 0 : -60 }} transition={{ duration: 0.5, ease: EASE }}>
        先把成本<span className="accent-word">摊清。</span>
      </motion.h2>
      <div className="ledger-table">
        <div className="ledger-table-head"><span>成本拆分</span><span>按单位 / 批次归集</span><span>成本快照</span></div>
        {costs.map((cost, i) => (
          <motion.div
            className={`ledger-row ledger-row-${i + 1}`}
            key={cost.index}
            initial={{ opacity: 0, x: -38 }}
            animate={{ opacity: phase >= i + 2 ? 1 : 0, x: phase >= i + 2 ? 0 : -38 }}
            transition={{ duration: 0.42, delay: i * 0.06, ease: EASE }}
          >
            <span className="ledger-num">{cost.index}</span>
            <strong>{cost.name}</strong>
            <span className="ledger-bar"><i style={{ width: cost.width }} /></span>
            <span className="ledger-unknown">— — —</span>
          </motion.div>
        ))}
        <div className="ledger-foot"><span>固定费用 + 物流</span><span>÷ 订购数量</span><span>→</span><span>单位成本</span></div>
      </div>
      <div className="cost-rules">
        <motion.div
          className="rule-label rule-floor"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: phase >= 4 ? 1 : 0 }}
          transition={{ duration: 0.62, ease: EASE }}
        >
          <span>最低毛利率</span><b>成本底线</b>
        </motion.div>
        <motion.div
          className="rule-label rule-target"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: phase >= 3 ? 1 : 0 }}
          transition={{ duration: 0.72, delay: 0.12, ease: EASE }}
        >
          <span>目标毛利率</span><b>目标参考</b>
        </motion.div>
      </div>
      <motion.div className="ledger-caption" animate={{ opacity: phase >= 4 ? 1 : 0.2 }}>
        演示规则 · 保存时成本快照 · 不替代人工判断
      </motion.div>
      <motion.div
        className="price-arc-carrier"
        initial={{ rotate: 0, scale: 0.5, opacity: 0 }}
        animate={{ rotate: phase >= 5 ? -62 : 0, scale: phase >= 5 ? 1 : 0.5, opacity: phase >= 5 ? 1 : 0 }}
        transition={{ duration: 0.55, ease: EASE }}
      />
      <motion.div className="ledger-spine" animate={{ scaleY: phase >= 5 ? 1.18 : 1 }} />
    </motion.section>
  );
}

export function Scene03() {
  const [phase, setPhase] = useState(0);
  useSceneTimer([
    { time: 600, callback: () => setPhase(1) },
    { time: 1850, callback: () => setPhase(2) },
    { time: 2920, callback: () => setPhase(3) },
    { time: 3970, callback: () => setPhase(4) },
    { time: 4750, callback: () => setPhase(5) },
    { time: 5450, callback: () => setPhase(6) },
  ]);
  return (
    <motion.section
      className="film-scene reference-scene"
      initial={{ opacity: 0, clipPath: 'circle(0% at 73% 50%)' }}
      animate={{ opacity: 1, clipPath: 'circle(130% at 73% 50%)' }}
      exit={{ opacity: 0, scale: 1.035, filter: 'blur(8px)', transition: { duration: 0.34 } }}
      transition={{ duration: 0.66, ease: EASE }}
    >
      <SceneNumber n="03" label="PRICE REFERENCES" />
      <div className="reference-copy">
        <motion.h2 className="headline reference-headline" initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.58, ease: EASE }}>
          参考，<br /><span className="accent-word">不是决定。</span>
        </motion.h2>
        <motion.p className="mono-copy" animate={{ opacity: phase >= 5 ? 1 : 0.54 }}>
          预测历史成交单价；<br />不代表利润最优价或购买概率
        </motion.p>
      </div>
      <div className="dial-stage">
        <motion.div
          className="dial-shadow"
          initial={{ scale: 0.74, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.72, ease: EASE }}
        />
        <motion.div
          className="dial-ring dial-ring-outer"
          initial={{ rotate: -140, opacity: 0 }}
          animate={{ rotate: phase >= 1 ? 0 : -140, opacity: phase >= 1 ? 1 : 0 }}
          transition={{ duration: 1.05, ease: EASE }}
        />
        <motion.div className="dial-ring dial-ring-inner" initial={{ scale: 0.7, opacity: 0 }} animate={{ scale: phase >= 1 ? 1 : 0.7, opacity: phase >= 1 ? 1 : 0 }} transition={{ duration: 0.72, delay: 0.15, ease: EASE }} />
        <svg className="dial-ticks" viewBox="0 0 420 420" aria-hidden="true">
          {Array.from({ length: 48 }, (_, i) => {
            const angle = (i * 7.5 - 90) * Math.PI / 180;
            const major = i % 4 === 0;
            const r1 = major ? 174 : 181;
            const r2 = 192;
            const x1 = 210 + Math.cos(angle) * r1;
            const y1 = 210 + Math.sin(angle) * r1;
            const x2 = 210 + Math.cos(angle) * r2;
            const y2 = 210 + Math.sin(angle) * r2;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className={major ? 'dial-tick major' : 'dial-tick'} />;
          })}
        </svg>
        <motion.div
          className="history-arc"
          initial={{ clipPath: 'inset(0 100% 0 0)' }}
          animate={{ clipPath: phase >= 1 ? 'inset(0 0% 0 0)' : 'inset(0 100% 0 0)' }}
          transition={{ duration: 0.8, ease: EASE }}
        />
        <motion.div className="model-ring" initial={{ scale: 0.55, opacity: 0 }} animate={{ scale: phase >= 2 ? 1 : 0.55, opacity: phase >= 2 ? 1 : 0 }} transition={{ duration: 0.64, ease: EASE }} />
        <motion.div className="floor-ring" initial={{ scale: 0.65, opacity: 0 }} animate={{ scale: phase >= 3 ? 1 : 0.65, opacity: phase >= 3 ? 1 : 0 }} transition={{ duration: 0.5, ease: EASE }} />
        <motion.div
          className="quote-marker"
          initial={{ x: 44, y: -31, rotate: -20, scale: 0.6 }}
          animate={{ x: phase >= 4 ? 0 : 44, y: phase >= 4 ? 0 : -31, rotate: phase >= 4 ? 0 : -20, scale: phase >= 4 ? 1 : 0.6 }}
          transition={{ ...snap }}
        >
          <span>人工拟报价</span><b />
        </motion.div>
        <motion.div className="dial-center" animate={{ scale: phase >= 4 ? 1 : 0.9 }} transition={{ duration: 0.4, ease: EASE }}>
          <span>PRICE</span>
          <strong>参考</strong>
          <i>NOT A DECISION</i>
        </motion.div>
        <AnimatePresence>
          {phase >= 1 && (
            <motion.span className="dial-label label-history" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }}>
              可比历史
            </motion.span>
          )}
          {phase >= 2 && (
            <motion.span className="dial-label label-model" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }}>
              历史成交价预测
            </motion.span>
          )}
          {phase >= 3 && (
            <motion.span className="dial-label label-floor" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }}>
              成本底线
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <div className="reference-footer"><span>合成数据示意 · 非量化刻度</span><span>历史统计 / 模型预测 / 人工拟价</span></div>
      <motion.div className="dial-aperture" animate={{ scale: phase >= 6 ? 1.45 : 0.35, opacity: phase >= 6 ? 0.84 : 0 }} transition={{ duration: 0.62, ease: EASE }} />
    </motion.section>
  );
}

export function Scene04() {
  const [phase, setPhase] = useState(0);
  useSceneTimer([
    { time: 550, callback: () => setPhase(1) },
    { time: 1500, callback: () => setPhase(2) },
    { time: 2550, callback: () => setPhase(3) },
    { time: 3250, callback: () => setPhase(4) },
    { time: 4350, callback: () => setPhase(5) },
    { time: 5250, callback: () => setPhase(6) },
  ]);
  return (
    <motion.section
      className="film-scene review-scene"
      initial={{ opacity: 0, clipPath: 'inset(0 0 100% 0)' }}
      animate={{ opacity: 1, clipPath: 'inset(0 0 0% 0)' }}
      exit={{ opacity: 0, scale: 0.97, rotateX: 7, filter: 'blur(7px)', transition: { duration: 0.32 } }}
      transition={{ duration: 0.6, ease: EASE }}
    >
      <div className="review-panel" />
      <SceneNumber n="04" label="HUMAN REVIEW" />
      <div className="review-copy">
        <AnimatePresence mode="sync">
          <motion.h2
            key={phase >= 3 ? 'approval' : 'quote'}
            className="headline review-headline"
            initial={{ opacity: 0, y: 48, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -28, filter: 'blur(5px)', transition: { duration: 0.22 } }}
            transition={{ duration: 0.45, ease: EASE }}
          >
            {phase >= 3 ? <>人来<br /><span className="accent-word">审批。</span></> : <>人来<br /><span className="accent-word">拟价。</span></>}
          </motion.h2>
        </AnimatePresence>
        <motion.div className="review-ownership" animate={{ opacity: phase >= 2 ? 1 : 0.42 }}>
          销售提出报价<br /><span>模拟经理审核</span>
        </motion.div>
      </div>

      <motion.div
        className="quote-sheet"
        initial={{ opacity: 0, x: 18, y: 54, rotate: 7, scale: 0.86 }}
        animate={{ opacity: 1, x: 0, y: 0, rotate: phase >= 6 ? 0 : 2.7, scale: phase >= 6 ? 0.9 : 1 }}
        transition={{ duration: 0.76, ease: EASE }}
      >
        <span className="sheet-registration" />
        <div className="sheet-header">
          <span>QUOTATION / DEMO</span><span>V 01</span>
        </div>
        <div className="sheet-title">制造报价记录</div>
        <div className="sheet-subtitle">保存时成本快照 / 仅供演示</div>
        <div className="sheet-rule" />
        <div className="sheet-fields">
          <div><span>产品</span><i /><b>合成示例</b></div>
          <div><span>报价</span><i /><b>人工拟定</b></div>
          <div><span>有效期</span><i /><b>已记录</b></div>
        </div>
        <div className="sheet-version-stack">
          <motion.div className="version-back" animate={{ y: phase >= 2 ? 12 : 0, x: phase >= 2 ? 12 : 0, rotate: phase >= 2 ? 2 : 0 }} transition={{ duration: 0.45, ease: EASE }}>
            <span>V 00</span><i />
          </motion.div>
          <motion.div className="version-front" animate={{ y: phase >= 2 ? -7 : 0 }} transition={{ duration: 0.4, ease: EASE }}>
            <span>V 01</span><i />
          </motion.div>
        </div>
        <motion.div className="pending-stamp" initial={{ opacity: 0, scale: 1.4, rotate: -7 }} animate={{ opacity: phase >= 3 ? 1 : 0, scale: phase >= 3 ? 1 : 1.4, rotate: -7 }} transition={{ duration: 0.35, ease: EASE }}>
          待模拟审批
        </motion.div>
        <motion.div className="approved-stamp" initial={{ opacity: 0, scale: 1.45, rotate: 6 }} animate={{ opacity: phase >= 4 ? 1 : 0, scale: phase >= 4 ? 1 : 1.45, rotate: 6 }} transition={{ duration: 0.42, ease: EASE }}>
          <b>已批准</b><span>演示</span>
        </motion.div>
        <motion.div className="sheet-audit" animate={{ opacity: phase >= 5 ? 1 : 0.2 }}>
          <span>成本快照</span><i /><span>审批记录</span><i /><span>操作留痕</span>
        </motion.div>
      </motion.div>
      <div className="review-caption">报价版本快照 · 操作记录</div>
      <motion.div className="archive-seal-carrier" animate={{ scale: phase >= 6 ? 1 : 0.4, rotate: phase >= 6 ? 0 : 18, opacity: phase >= 6 ? 1 : 0 }} transition={{ duration: 0.52, ease: EASE }}>
        <i />
      </motion.div>
    </motion.section>
  );
}

export function Scene05() {
  const [phase, setPhase] = useState(0);
  useSceneTimer([
    { time: 520, callback: () => setPhase(1) },
    { time: 1450, callback: () => setPhase(2) },
    { time: 2850, callback: () => setPhase(3) },
    { time: 3920, callback: () => setPhase(4) },
    { time: 4750, callback: () => setPhase(5) },
    { time: 5200, callback: () => setPhase(6) },
  ]);
  const records = [
    { text: '成本快照', x: '-21vmin', y: '-10vmin', at: 1 },
    { text: '审批记录', x: '21vmin', y: '-10vmin', at: 2 },
    { text: 'CSV / 可打印报价单', x: '0vmin', y: '15vmin', at: 3 },
  ];
  return (
    <motion.section
      className="film-scene archive-scene"
      initial={{ opacity: 0, clipPath: 'polygon(0 0,100% 0,100% 0,0 100%)' }}
      animate={{ opacity: 1, clipPath: 'polygon(0 0,100% 0,100% 100%,0 100%)' }}
      exit={{ opacity: 0, scale: 1.055, transition: { duration: 0.28 } }}
      transition={{ duration: 0.62, ease: EASE }}
    >
      <SceneNumber n="05" label="TRACEABLE RECORD" />
      <div className="archive-field" />
      <motion.div className="archive-title" animate={{ opacity: phase >= 1 ? 1 : 0, y: phase >= 1 ? 0 : 24 }} transition={{ duration: 0.48, ease: EASE }}>
        <h2 className="headline">每个报价，<br /><span>都有来处。</span></h2>
      </motion.div>
      <div className="archive-core">
        <motion.div className="archive-document" animate={{ scale: phase >= 3 ? 1 : 0.8, rotate: phase >= 3 ? 0 : -7, opacity: phase >= 3 ? 1 : 0 }} transition={{ duration: 0.62, ease: EASE }}>
          <div className="archive-doc-top"><span>QUOTE / RECORD</span><span>FILED</span></div>
          <div className="archive-doc-lines"><i /><i /><i /></div>
          <div className="archive-doc-seal"><i /></div>
        </motion.div>
        <motion.div className="archive-orbit" animate={{ rotate: phase >= 3 ? 0 : -34 }} transition={{ duration: 0.7, ease: EASE }} />
        {records.map((record) => (
          <motion.div
            key={record.text}
            className="archive-record-label"
            style={{
              left: `calc(50% + ${record.x})`,
              top: `calc(50% + ${record.y})`,
            } as CSSProperties}
            initial={{ opacity: 0, scale: 0.72 }}
            animate={{
              opacity: phase >= record.at ? 1 : 0,
              scale: phase >= 4 ? 0.76 : 1,
            }}
            transition={{ duration: 0.56, ease: EASE }}
          >
            <span>{record.text}</span><i />
          </motion.div>
        ))}
        <motion.div className="archive-seal" initial={{ scale: 0, rotate: -24 }} animate={{ scale: phase >= 2 ? 1 : 0, rotate: phase >= 5 ? 0 : -24 }} transition={{ ...snap }}>
          <span>APPROVED</span><b>演示</b>
        </motion.div>
      </div>
      <motion.div className="archive-lockup" animate={{ opacity: phase >= 4 ? 1 : 0, y: phase >= 4 ? 0 : 18 }} transition={{ duration: 0.42, ease: EASE }}>
        <span>SME MANUFACTURING QUOTATION ASSISTANT</span>
        <i>模拟演示 · 合成数据</i>
      </motion.div>
      <motion.div
        className="loop-register"
        animate={{
          scale: phase >= 6 ? 15 : 1,
          x: phase >= 6 ? '-42vmin' : 0,
          y: phase >= 6 ? '-8vmin' : 0,
          opacity: phase >= 6 ? 0.85 : 1,
        }}
        transition={{ duration: 0.7, ease: EASE }}
      />
      <div className="archive-border" />
    </motion.section>
  );
}
