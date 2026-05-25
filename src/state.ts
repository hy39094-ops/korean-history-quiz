// localStorage 기반 학습 상태: 문항별 정/오답 기록, 누적 응답, D-Day
import { useCallback, useEffect, useState } from "react";
import { ALL_ROUNDS, type Level, type Question } from "./data";

export interface QHistory {
  c: number; // correct count
  w: number; // wrong count
  t: number; // last answered timestamp
}

export type FeedbackMode = "immediate" | "deferred";

export interface AppState {
  history: Record<string, QHistory>; // question id → 기록
  dDay: string | null; // yyyy-mm-dd
  sessions: number;
  totalAnswered: number;
  seenRounds: { advanced: number[]; basic: number[] }; // 랜덤 회차에서 이미 푼 회차
  feedbackMode: FeedbackMode;
  autoAdvance: boolean; // 응답 후 2초 뒤 자동 다음 문제로
}

const KEY = "khq:state:v1";

const initial: AppState = {
  history: {},
  dDay: null,
  sessions: 0,
  totalAnswered: 0,
  seenRounds: { advanced: [], basic: [] },
  feedbackMode: "immediate",
  autoAdvance: true,
};

function load(): AppState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return initial;
    const parsed = JSON.parse(raw);
    return {
      ...initial,
      ...parsed,
      seenRounds: { ...initial.seenRounds, ...(parsed.seenRounds ?? {}) },
    };
  } catch {
    return initial;
  }
}

function save(s: AppState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* quota */
  }
}

export function useAppState() {
  const [state, setState] = useState<AppState>(() => load());

  useEffect(() => {
    save(state);
  }, [state]);

  const answer = useCallback((qid: string, correct: boolean) => {
    setState((prev) => {
      const cur = prev.history[qid] ?? { c: 0, w: 0, t: 0 };
      const next: QHistory = {
        c: cur.c + (correct ? 1 : 0),
        w: cur.w + (correct ? 0 : 1),
        t: Date.now(),
      };
      return {
        ...prev,
        history: { ...prev.history, [qid]: next },
        totalAnswered: prev.totalAnswered + 1,
      };
    });
  }, []);

  const incrementSessions = useCallback(() => {
    setState((prev) => ({ ...prev, sessions: prev.sessions + 1 }));
  }, []);

  const setDDay = useCallback((d: string | null) => {
    setState((prev) => ({ ...prev, dDay: d }));
  }, []);

  const resetProgress = useCallback(() => {
    setState((prev) => ({ ...initial, dDay: prev.dDay }));
  }, []);

  const markRoundSeen = useCallback((level: Level, round: number) => {
    setState((prev) => {
      const cur = prev.seenRounds[level];
      if (cur.includes(round)) return prev;
      return {
        ...prev,
        seenRounds: { ...prev.seenRounds, [level]: [...cur, round] },
      };
    });
  }, []);

  const resetSeenRounds = useCallback((level: Level) => {
    setState((prev) => ({
      ...prev,
      seenRounds: { ...prev.seenRounds, [level]: [] },
    }));
  }, []);

  const setFeedbackMode = useCallback((mode: FeedbackMode) => {
    setState((prev) => ({ ...prev, feedbackMode: mode }));
  }, []);

  const setAutoAdvance = useCallback((v: boolean) => {
    setState((prev) => ({ ...prev, autoAdvance: v }));
  }, []);

  return {
    state,
    answer,
    incrementSessions,
    setDDay,
    resetProgress,
    markRoundSeen,
    resetSeenRounds,
    setFeedbackMode,
    setAutoAdvance,
  };
}

// ───── 셀렉터/풀 ─────

function allQuestions(level?: Level): Question[] {
  const rs = level ? ALL_ROUNDS.filter((r) => r.level === level) : ALL_ROUNDS;
  return rs.flatMap((r) => r.questions.filter((q) => q.answer != null));
}

export function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** 무작위 N문제 (선택한 급수 풀에서) */
export function pickRandomQuestions(level: Level, n: number): Question[] {
  return shuffle(allQuestions(level)).slice(0, n);
}

/** 오답 노트: 한 번이라도 틀린 적 있는 문제 (자주 틀린 순) */
export function pickWrongQuestions(
  history: Record<string, QHistory>,
  level: Level,
  n: number,
): Question[] {
  const pool = allQuestions(level);
  const qmap = new Map(pool.map((q) => [q.id, q]));
  const ids = Object.entries(history)
    .filter(([, h]) => h.w > 0)
    .sort(([, a], [, b]) => {
      if (b.w !== a.w) return b.w - a.w;
      return b.t - a.t;
    })
    .map(([id]) => id)
    .filter((id) => qmap.has(id));
  return ids.map((id) => qmap.get(id)!).slice(0, n);
}

/** 한 번이라도 틀린 고유 문제 수 (현재 급수 기준) */
export function countWrongQuestions(
  history: Record<string, QHistory>,
  level: Level,
): number {
  const pool = allQuestions(level);
  const ids = new Set(pool.map((q) => q.id));
  let n = 0;
  for (const [id, h] of Object.entries(history)) {
    if (h.w > 0 && ids.has(id)) n++;
  }
  return n;
}

/** D-Day까지 남은 일수 */
export function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const target = new Date(iso + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}
