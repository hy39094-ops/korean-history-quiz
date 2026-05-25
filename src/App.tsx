import { useEffect, useMemo, useState } from "react";
import {
  ALL_ROUNDS,
  getAvailableLevels,
  getQuestions,
  getRoundsByLevel,
  type Level,
  type Question,
} from "./data";
import {
  countWrongQuestions,
  daysUntil,
  type FeedbackMode,
  pickRandomQuestions,
  pickWrongQuestions,
  shuffle,
  useAppState,
} from "./state";

type Mode = "randomRound" | "quick" | "full" | "wrong";

type View =
  | { name: "home" }
  | { name: "practice"; mode: Mode; questions: Question[]; timed: boolean; pickedRound?: number; preserveOrder?: boolean }
  | { name: "result"; mode: Mode; correct: number; total: number; missed: Question[]; pickedRound?: number; score: number; maxScore: number };

const LEVEL_LABEL: Record<Level, string> = {
  advanced: "심화 (1~3급)",
  basic: "기본 (4~6급)",
};

const MODE_META: Record<Mode, { title: string; sub: string; emoji: string; timed?: boolean }> = {
  randomRound: { title: "랜덤 회차", sub: "회차 하나 통째로", emoji: "🎲" },
  quick: { title: "빠른 모드", sub: "무작위 10문제", emoji: "⚡" },
  full: { title: "실전 모의고사", sub: "50문제 · 50분 타이머", emoji: "🎯", timed: true },
  wrong: { title: "오답 노트", sub: "내가 틀린 문제만", emoji: "📝" },
};

const FULL_MODE_SECONDS = 50 * 60;

const availableLevels = getAvailableLevels();
const DEFAULT_LEVEL: Level = availableLevels.includes("advanced") ? "advanced" : availableLevels[0] ?? "advanced";

const CIRCLES = ["①", "②", "③", "④", "⑤"];

function formatTime(s: number): string {
  const m = Math.max(0, Math.floor(s / 60));
  const ss = Math.max(0, s % 60);
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

export default function App() {
  const {
    state,
    answer,
    incrementSessions,
    setDDay,
    resetProgress,
    markRoundSeen,
    resetSeenRounds,
    setFeedbackMode,
    setAutoAdvance,
  } = useAppState();
  const [view, setView] = useState<View>({ name: "home" });
  const [level, setLevel] = useState<Level>(DEFAULT_LEVEL);
  const rounds = useMemo(() => getRoundsByLevel(level), [level]);

  const startMode = (mode: Mode) => {
    let qs: Question[] = [];
    let pickedRound: number | undefined;
    let preserveOrder = false;
    if (mode === "randomRound") {
      const seen = state.seenRounds[level];
      const remaining = rounds.filter((r) => !seen.includes(r.round));
      if (remaining.length === 0) return;
      const choice = remaining[Math.floor(Math.random() * remaining.length)];
      pickedRound = choice.round;
      qs = getQuestions(choice.round, level);
      markRoundSeen(level, choice.round);
      preserveOrder = true;
    } else if (mode === "quick") qs = pickRandomQuestions(level, 10);
    else if (mode === "full") qs = pickRandomQuestions(level, 50);
    else if (mode === "wrong") qs = pickWrongQuestions(state.history, level, 30);
    if (qs.length === 0) return;
    incrementSessions();
    setView({
      name: "practice",
      mode,
      questions: qs,
      timed: !!MODE_META[mode].timed,
      pickedRound,
      preserveOrder,
    });
  };

  const startSpecificRound = (roundNum: number) => {
    const qs = getQuestions(roundNum, level);
    if (qs.length === 0) return;
    markRoundSeen(level, roundNum);
    incrementSessions();
    setView({
      name: "practice",
      mode: "randomRound",
      questions: qs,
      timed: false,
      pickedRound: roundNum,
      preserveOrder: true,
    });
  };

  if (view.name === "practice") {
    return (
      <Practice
        mode={view.mode}
        questions={view.questions}
        timed={view.timed}
        pickedRound={view.pickedRound}
        preserveOrder={!!view.preserveOrder}
        feedbackMode={state.feedbackMode}
        autoAdvance={state.autoAdvance}
        onAnswer={answer}
        onDone={(c, t, m, s, ms) =>
          setView({
            name: "result",
            mode: view.mode,
            correct: c,
            total: t,
            missed: m,
            pickedRound: view.pickedRound,
            score: s,
            maxScore: ms,
          })
        }
        onAbort={() => setView({ name: "home" })}
      />
    );
  }

  if (view.name === "result") {
    return (
      <Result
        mode={view.mode}
        correct={view.correct}
        total={view.total}
        missed={view.missed}
        pickedRound={view.pickedRound}
        score={view.score}
        maxScore={view.maxScore}
        onHome={() => setView({ name: "home" })}
        onRetry={() => startMode(view.mode)}
      />
    );
  }

  return (
    <Home
      state={state}
      level={level}
      setLevel={setLevel}
      rounds={rounds}
      onSetDDay={setDDay}
      onResetProgress={resetProgress}
      onResetSeenRounds={() => resetSeenRounds(level)}
      onSetFeedbackMode={setFeedbackMode}
      onSetAutoAdvance={setAutoAdvance}
      onStartMode={startMode}
      onStartRound={startSpecificRound}
    />
  );
}

function Home(props: {
  state: ReturnType<typeof useAppState>["state"];
  level: Level;
  setLevel: (l: Level) => void;
  rounds: ReturnType<typeof getRoundsByLevel>;
  onSetDDay: (d: string | null) => void;
  onResetProgress: () => void;
  onResetSeenRounds: () => void;
  onSetFeedbackMode: (m: FeedbackMode) => void;
  onSetAutoAdvance: (v: boolean) => void;
  onStartMode: (m: Mode) => void;
  onStartRound: (r: number) => void;
}) {
  const {
    state,
    level,
    setLevel,
    rounds,
    onSetDDay,
    onResetSeenRounds,
    onSetFeedbackMode,
    onSetAutoAdvance,
    onStartMode,
    onStartRound,
  } = props;
  const dDays = daysUntil(state.dDay);
  const wrongCount = countWrongQuestions(state.history, level);
  const seenForLevel = state.seenRounds[level];
  const remainingRounds = rounds.filter((r) => !seenForLevel.includes(r.round));
  const totalAvailable = useMemo(
    () => ALL_ROUNDS.filter((r) => r.level === level).reduce((acc, r) => acc + r.total, 0),
    [level],
  );
  const sortedRounds = [...rounds].sort((a, b) => b.round - a.round);
  const [selectedRound, setSelectedRound] = useState<number>(sortedRounds[0]?.round ?? 0);
  useEffect(() => {
    if (sortedRounds.length > 0 && !sortedRounds.find((r) => r.round === selectedRound)) {
      setSelectedRound(sortedRounds[0].round);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level]);

  return (
    <div className="screen">
      <header className="hero">
        <div className="hero-title">
          <span className="hero-emoji">📜</span>
          <div className="hero-title-text">
            <span className="hero-year-tag">2026 최신 기출</span>
            <h1>한국사능력검정시험</h1>
          </div>
        </div>
        <p className="hero-sub">최근 기출로 실전처럼 풀어보기</p>

        <div className="hero-stats">
          <Stat
            label={`응시한 ${LEVEL_LABEL[level].split(" ")[0]} 회차`}
            value={`${seenForLevel.length} / ${rounds.length}`}
            onReset={seenForLevel.length > 0 ? onResetSeenRounds : undefined}
          />
          <Stat
            label="D-Day"
            value={
              dDays === null
                ? "—"
                : dDays > 0
                  ? `D-${dDays}`
                  : dDays === 0
                    ? "D-Day"
                    : `D+${-dDays}`
            }
          />
        </div>

        <DDayInput value={state.dDay} onChange={onSetDDay} />
      </header>

      <section className="section">
        <div className="tabs">
          {(["advanced", "basic"] as Level[]).map((l) => {
            const available = availableLevels.includes(l);
            return (
              <button
                key={l}
                className={`tab ${level === l ? "tab-active" : ""}`}
                onClick={() => available && setLevel(l)}
                disabled={!available}
              >
                {LEVEL_LABEL[l]}
                {!available && " · 준비중"}
              </button>
            );
          })}
        </div>
      </section>

      <section className="section">
        <label className="label">결과 확인 방식</label>
        <div className="feedback-mode-toggle">
          <button
            className={`feedback-mode-btn ${state.feedbackMode === "immediate" ? "feedback-mode-btn-active" : ""}`}
            onClick={() => onSetFeedbackMode("immediate")}
          >
            <span className="feedback-mode-title">즉시 확인</span>
            <span className="feedback-mode-sub">문제 풀면 바로 정답 표시</span>
          </button>
          <button
            className={`feedback-mode-btn ${state.feedbackMode === "deferred" ? "feedback-mode-btn-active" : ""}`}
            onClick={() => onSetFeedbackMode("deferred")}
          >
            <span className="feedback-mode-title">한 번에 확인</span>
            <span className="feedback-mode-sub">다 풀고 결과 한꺼번에</span>
          </button>
        </div>
      </section>

      <section className="section">
        <label className="switch-row">
          <div className="switch-info">
            <div className="switch-title">자동 다음 문제</div>
            <div className="switch-sub">답 선택하면 2초 후 다음 문제로 자동 이동</div>
          </div>
          <input
            type="checkbox"
            className="switch-input"
            checked={state.autoAdvance}
            onChange={(e) => onSetAutoAdvance(e.target.checked)}
          />
          <span className="switch-track">
            <span className="switch-thumb" />
          </span>
        </label>
      </section>

      <section className="section">
        <label className="label">회차 선택</label>
        <div className="round-picker">
          <select
            className="select"
            value={selectedRound}
            onChange={(e) => setSelectedRound(Number(e.target.value))}
          >
            {sortedRounds.map((r) => {
              const isSeen = seenForLevel.includes(r.round);
              return (
                <option key={r.round} value={r.round}>
                  제{r.round}회 · {r.total}문제{isSeen ? " · 응시함" : ""}
                </option>
              );
            })}
          </select>
          <button
            className="primary-btn round-picker-btn"
            onClick={() => selectedRound && onStartRound(selectedRound)}
            disabled={!selectedRound}
          >
            시작
          </button>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">학습 모드</h2>
          {seenForLevel.length > 0 && (
            <button className="text-link" onClick={onResetSeenRounds} title="본 회차 초기화">
              ↻ 회차 초기화
            </button>
          )}
        </div>
        <div className="mode-grid">
          {(Object.keys(MODE_META) as Mode[]).map((m) => {
            const isExhausted = m === "randomRound" && remainingRounds.length === 0;
            const isWrongEmpty = m === "wrong" && wrongCount === 0;
            const empty = isExhausted || isWrongEmpty;
            let countLabel: string;
            if (m === "wrong") {
              countLabel = wrongCount === 0 ? "오답 없음" : `${Math.min(wrongCount, 30)}문제`;
            } else if (m === "randomRound") {
              countLabel = isExhausted
                ? "초기화 필요"
                : `${remainingRounds.length}/${rounds.length}회차 남음`;
            } else if (m === "quick") {
              countLabel = "10문제";
            } else {
              countLabel = "50문제";
            }
            return (
              <button
                key={m}
                className={`mode-card ${empty ? "mode-card-empty" : ""}`}
                onClick={() => !empty && onStartMode(m)}
                disabled={empty}
              >
                <span className="mode-emoji">{MODE_META[m].emoji}</span>
                <span className="mode-title">{MODE_META[m].title}</span>
                <span className="mode-sub">{MODE_META[m].sub}</span>
                <span className="mode-count">{countLabel}</span>
              </button>
            );
          })}
        </div>
        <p className="hint">
          현재 {LEVEL_LABEL[level]} 풀에 {totalAvailable}문제 보유 · 오답 노트 {wrongCount}개
        </p>
      </section>

      <footer className="footer">
        <div className="footer-attribution">문제 출처: 국사편찬위원회 한국사능력검정시험</div>
        <div className="footer-note">컨텐츠는 2차 가공되지 않으며 학습 목적으로만 사용됩니다.</div>
      </footer>
    </div>
  );
}

function Stat({ label, value, onReset }: { label: string; value: string; onReset?: () => void }) {
  return (
    <div className="stat">
      {onReset && (
        <button className="stat-reset" onClick={onReset} aria-label="초기화" title="초기화">
          ↻
        </button>
      )}
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function DDayInput({ value, onChange }: { value: string | null; onChange: (d: string | null) => void }) {
  return (
    <div className="dday-input">
      <label>시험일 설정</label>
      <input type="date" value={value ?? ""} onChange={(e) => onChange(e.target.value || null)} />
    </div>
  );
}

interface Response {
  selected: number;
  isCorrect: boolean;
}

function Practice(props: {
  mode: Mode;
  questions: Question[];
  timed: boolean;
  pickedRound?: number;
  preserveOrder?: boolean;
  feedbackMode: FeedbackMode;
  autoAdvance: boolean;
  onAnswer: (qid: string, correct: boolean) => void;
  onDone: (correct: number, total: number, missed: Question[], score: number, maxScore: number) => void;
  onAbort: () => void;
}) {
  const { questions, timed, preserveOrder, feedbackMode, autoAdvance, onAnswer, onDone, onAbort } = props;
  const isDeferred = feedbackMode === "deferred";
  const list = useMemo(
    () => (preserveOrder ? [...questions].sort((a, b) => a.number - b.number) : shuffle(questions)),
    [questions, preserveOrder],
  );
  const [idx, setIdx] = useState(0);
  const [responses, setResponses] = useState<Record<number, Response>>({});
  const [secondsLeft, setSecondsLeft] = useState(FULL_MODE_SECONDS);

  const correctCount = Object.values(responses).filter((r) => r.isCorrect).length;
  const answeredCount = Object.keys(responses).length;
  const missed = list.filter((_, i) => responses[i] && !responses[i].isCorrect);
  const unansweredIdx = list.map((_, i) => i).filter((i) => !responses[i]);
  const score = list.reduce((acc, q, i) => {
    const r = responses[i];
    return r && r.isCorrect && q.points ? acc + q.points : acc;
  }, 0);
  const maxScore = list.reduce((acc, q) => acc + (q.points || 0), 0);

  const finalizeDone = () => onDone(correctCount, list.length, missed, score, maxScore);

  useEffect(() => {
    if (!timed) return;
    if (secondsLeft <= 0) {
      finalizeDone();
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft, timed]);

  if (list.length === 0) {
    return (
      <div className="screen center">
        <p>풀 수 있는 문제가 없어요.</p>
        <button className="primary-btn" onClick={onAbort}>홈으로</button>
      </div>
    );
  }

  // 문제 전환 시 hover/focus 잔상 제거
  useEffect(() => {
    (document.activeElement as HTMLElement | null)?.blur();
  }, [idx]);

  const q = list[idx];
  const currentResponse = responses[idx];
  const revealed = !!currentResponse && !isDeferred;
  const selected = currentResponse?.selected ?? null;
  const progress = (answeredCount / list.length) * 100;
  const circles = q.choices.length === 4 ? CIRCLES.slice(0, 4) : CIRCLES;

  const onSelect = (i: number) => {
    if (revealed) return;
    const isCorrect = q.answer === i + 1;
    onAnswer(q.id, isCorrect);
    setResponses((prev) => ({ ...prev, [idx]: { selected: i, isCorrect } }));
    // 자동 다음 문제 (옵션). 끄면 사용자가 그리드에서 직접 선택.
    if (!autoAdvance) return;
    setTimeout(() => {
      setIdx((curIdx) => {
        const unanswered = list
          .map((_, i2) => i2)
          .filter((i2) => i2 !== curIdx && !responses[i2]);
        const after = unanswered.find((i2) => i2 > curIdx);
        const next = after ?? unanswered[0];
        return next ?? curIdx;
      });
    }, 2000);
  };

  const jumpTo = (i: number) => setIdx(i);

  const totalAnswered = answeredCount;
  const allAnswered = unansweredIdx.length === 0;

  return (
    <div className="screen screen-practice">
      <header className="practice-header">
        <button className="icon-btn" onClick={onAbort}>←</button>
        <div className="practice-progress">
          <div className="practice-progress-bar" style={{ width: `${progress}%` }} />
        </div>
        <span className="practice-count">
          {totalAnswered} / {list.length}
        </span>
      </header>

      <div className="meta-row">
        <span className="meta-chip">제{q.round}회 {q.level === "advanced" ? "심화" : "기본"}</span>
        <span className="meta-chip">Q{q.number}</span>
        {q.points && <span className="meta-chip">{q.points}점</span>}
      </div>

      <div className="question-grid">
        <div className="question-grid-cells">
          {list.map((qi, i) => {
            const resp = responses[i];
            const isCurrent = i === idx;
            let stateClass = " qg-cell-empty";
            if (resp) {
              if (isDeferred) stateClass = " qg-cell-answered";
              else stateClass = resp.isCorrect ? " qg-cell-correct" : " qg-cell-wrong";
            }
            const cls = "qg-cell" + (isCurrent ? " qg-cell-current" : "") + stateClass;
            return (
              <button key={i} className={cls} onClick={() => jumpTo(i)} aria-label={`${qi.number}번 문항으로 이동`}>
                {qi.number}
              </button>
            );
          })}
        </div>
        {allAnswered && (
          <div className="question-grid-foot">
            <button className="primary-btn qg-result-btn" onClick={finalizeDone}>
              결과 보기
            </button>
          </div>
        )}
      </div>

      <div className="practice-body">
        <div className="practice-main">

      {timed && (
        <div className={`timer ${secondsLeft <= 300 ? "timer-warn" : ""} ${secondsLeft <= 60 ? "timer-danger" : ""}`}>
          ⏱️ {formatTime(secondsLeft)}
        </div>
      )}

      <div className="question-card">
        {/* 이미지가 있으면 문제 텍스트는 숨김 (이미지에 모든 내용 포함됨) */}
        {q.image_url ? (
          <div className="question-image-wrap">
            <img className="question-image" src={q.image_url} alt={`문항 ${q.number} 자료`} />
          </div>
        ) : (
          q.question && (
            <p className="question-text">
              <strong>Q{q.number}.</strong> {q.question}
            </p>
          )
        )}

        <div className="choices">
          {q.choices.map((_, i) => {
            const isAnswer = q.answer === i + 1;
            const isSelected = selected === i;
            const cls =
              "choice" +
              (revealed && isAnswer ? " choice-correct" : "") +
              (revealed && isSelected && !isAnswer ? " choice-wrong" : "") +
              (isSelected && !revealed ? " choice-selected" : "");
            return (
              <button key={i} className={cls} onClick={() => onSelect(i)} disabled={revealed} aria-label={`${i + 1}번 선택`}>
                <span className="choice-num">{circles[i]}</span>
              </button>
            );
          })}
        </div>


        {revealed && (() => {
          const isCorrect = q.answer === (selected ?? -1) + 1;
          return (
            <div className={`feedback ${isCorrect ? "feedback-ok" : "feedback-no"}`}>
              <div className="feedback-row">
                <span className={`feedback-icon ${isCorrect ? "" : "feedback-icon-x"}`}>
                  {isCorrect ? "✓" : "✕"}
                </span>
                <span className="feedback-title">{isCorrect ? "잘했어요" : "정답은"}</span>
              </div>
              {!isCorrect && q.answer != null && (
                <div className="feedback-answer">
                  <span className="feedback-answer-num">{circles[q.answer - 1]}</span>
                </div>
              )}
            </div>
          );
        })()}
      </div>

        </div>
      </div>
    </div>
  );
}

function Result(props: {
  mode: Mode;
  correct: number;
  total: number;
  missed: Question[];
  pickedRound?: number;
  score: number;
  maxScore: number;
  onHome: () => void;
  onRetry: () => void;
}) {
  const { mode, correct, total, missed, pickedRound, score, maxScore, onHome, onRetry } = props;
  const rate = maxScore === 0 ? 0 : score / maxScore;
  const passed = score >= 60; // 한능검 심화 합격선 60점

  const title = passed ? "합격권이에요" : rate >= 0.4 ? "조금만 더 해볼까요" : "한 번 더 풀어볼까요";
  const emoji = passed ? "🎉" : rate >= 0.4 ? "📚" : "📝";

  return (
    <div className="screen">
      <div className="result-card">
        <div className="result-emoji">{emoji}</div>
        <h2 className="result-title">{title}</h2>
        <p className="result-sub">
          {MODE_META[mode].title}
          {pickedRound ? ` · 제${pickedRound}회` : ""}
        </p>

        <div className="result-score">
          <div className="result-rate">
            {score}<span className="result-rate-of"> / {maxScore}점</span>
          </div>
          <div className="result-frac">정답 {correct} / {total}문항</div>
        </div>
        <div className="result-progress">
          <div className="result-progress-bar" style={{ width: `${rate * 100}%` }} />
        </div>

        {missed.length > 0 && (
          <div className="result-missed">
            <strong>틀린 문제 {missed.length}개</strong>
            <p>오답 노트에 자동으로 쌓였어요. 시간 날 때 다시 풀어보세요.</p>
          </div>
        )}
      </div>

      <div className="result-actions">
        <button className="secondary-btn" onClick={onHome}>홈으로</button>
        <button className="primary-btn" onClick={onRetry}>한 번 더</button>
      </div>
    </div>
  );
}
