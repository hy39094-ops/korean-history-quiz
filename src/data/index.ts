// 자동 로딩: src/data/round-*.json 전부 가져오기
const modules = import.meta.glob<RoundFile>("./round-*.json", { eager: true });

export type Level = "advanced" | "basic";

// UI에 노출할 회차만 추림. 빈 배열이면 전체 노출.
// 수동 크롭으로 품질 보정한 회차만 우선 노출 중. 추가하려면 여기에 항목 넣으면 됨.
const ROUND_ALLOWLIST: Array<{ round: number; level: Level }> = [
  { round: 78, level: "advanced" },
  { round: 77, level: "advanced" },
  { round: 77, level: "basic" },
  { round: 76, level: "advanced" },
  { round: 75, level: "advanced" },
  { round: 75, level: "basic" },
  { round: 74, level: "advanced" },
  { round: 73, level: "basic" },
  { round: 73, level: "advanced" },
  { round: 72, level: "advanced" },
  { round: 71, level: "advanced" },
  { round: 71, level: "basic" },
  { round: 70, level: "advanced" },
  { round: 69, level: "basic" },
  { round: 69, level: "advanced" },
  { round: 68, level: "advanced" },
  { round: 67, level: "basic" },
  { round: 67, level: "advanced" },
  { round: 66, level: "advanced" },
  { round: 66, level: "basic" },
  { round: 65, level: "advanced" },
  { round: 64, level: "advanced" },
  { round: 63, level: "basic" },
  { round: 63, level: "advanced" },
  { round: 61, level: "basic" },
  { round: 61, level: "advanced" },
  { round: 60, level: "advanced" },
  { round: 59, level: "advanced" },
  { round: 58, level: "basic" },
  { round: 57, level: "basic" },
  { round: 57, level: "advanced" },
  { round: 62, level: "advanced" },
  { round: 60, level: "basic" },
  { round: 58, level: "advanced" },
];

function isAllowed(round: number, level: Level): boolean {
  if (ROUND_ALLOWLIST.length === 0) return true;
  return ROUND_ALLOWLIST.some((a) => a.round === round && a.level === level);
}

export interface Question {
  id: string;
  round: number;
  level: Level;
  number: number;
  question: string;
  choices: string[];
  answer: number | null;
  points: number | null;
  has_image: boolean;
  image_url: string | null;
  image_is_full_page: boolean;
}

interface RoundFile {
  default: {
    round: number;
    level: Level;
    choice_count: number;
    total: number;
    parse_failed_numbers: number[];
    image_dependent_count: number;
    image_rendered_count: number;
    image_only_pdf?: boolean;
    questions: Question[];
  };
}

export interface Round {
  round: number;
  level: Level;
  choice_count: number;
  total: number;
  image_only_pdf: boolean;
  questions: Question[];
}

const ALL: Round[] = Object.values(modules)
  .map((m) => m.default)
  .filter((r) => r.total > 0)
  .filter((r) => isAllowed(r.round, r.level))
  .map((r) => ({
    round: r.round,
    level: r.level,
    choice_count: r.choice_count,
    total: r.total,
    image_only_pdf: r.image_only_pdf ?? false,
    questions: r.questions,
  }))
  .sort((a, b) => b.round - a.round);

export const ALL_ROUNDS = ALL;

export function getRoundsByLevel(level: Level): Round[] {
  return ALL.filter((r) => r.level === level);
}

export function getAvailableLevels(): Level[] {
  const levels = new Set(ALL.map((r) => r.level));
  return Array.from(levels);
}

export function getRound(round: number, level: Level): Round | undefined {
  return ALL.find((r) => r.round === round && r.level === level);
}

export function getQuestions(round: number, level: Level): Question[] {
  const r = getRound(round, level);
  if (!r) return [];
  return r.questions.filter((q) => q.answer != null || q.image_is_full_page);
}
