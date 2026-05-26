import { useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, Text, View } from "react-native";

import {
  getCertificationBetaOptions,
  includeCertificationInRoadmap,
} from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function ResultScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, analysisResult, lastSkills, setActiveRoadmap } = useAnalysis();
  const hasResult = !!analysisResult;
  const hasRoadmap = !!activeRoadmap?.id;
  const targetRole =
    analysisResult?.target_role ??
    analysisResult?.future_job ??
    analysisResult?.job_target ??
    activeRoadmap?.job_target ??
    "-";
  const [certificationOptions, setCertificationOptions] = useState([]);
  const [pendingCertification, setPendingCertification] = useState(null);
  const [certificationError, setCertificationError] = useState("");

  useEffect(() => {
    let mounted = true;
    if (targetRole !== "Data Scientist" || !hasRoadmap) {
      setCertificationOptions([]);
      return () => {
        mounted = false;
      };
    }
    getCertificationBetaOptions(targetRole)
      .then((options) => {
        if (mounted) setCertificationOptions(options);
      })
      .catch(() => {
        if (mounted) setCertificationError("자격증 일정을 불러오지 못했습니다.");
      });
    return () => {
      mounted = false;
    };
  }, [hasRoadmap, targetRole]);

  const includeCertification = async (code) => {
    setPendingCertification(code);
    setCertificationError("");
    try {
      const roadmap = await includeCertificationInRoadmap(code);
      setActiveRoadmap(roadmap);
      setCertificationOptions((current) =>
        current.map((option) =>
          option.code === code ? { ...option, is_selected: true } : option,
        ),
      );
    } catch (error) {
      setCertificationError(
        error.response?.data?.detail ?? "자격증 준비 계획을 추가하지 못했습니다.",
      );
    } finally {
      setPendingCertification(null);
    }
  };

  if (!hasResult && !hasRoadmap) {
    return (
      <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
            분석 결과
          </Text>
          <Text style={commonStyles.bodyText}>먼저 분석을 실행해주세요.</Text>
          <Pressable
            style={[commonStyles.primaryButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Input")}
          >
            <Text style={commonStyles.primaryButtonText}>새로 분석하기</Text>
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  const currentSkills = withFallback(toArray(analysisResult?.current_skills), lastSkills);
  const recommendedSkills = toArray(
    analysisResult?.recommended_skills ??
      analysisResult?.recommended_learning ??
      analysisResult?.roadmap?.flatMap((step) => step.items ?? []),
  );
  const roadmapLearning = extractRoadmapLearning(activeRoadmap);
  const recommendedLearning = withFallback(recommendedSkills, roadmapLearning);
  const missingSkills = withFallback(
    toArray(analysisResult?.missing_skills),
    recommendedLearning.filter((skill) => !includesIgnoreCase(currentSkills, skill)),
  );
  const recommendedProjects = withFallback(
    toArray(
      analysisResult?.recommended_projects ??
        analysisResult?.roadmap?.map((step) => translateProjectTitle(step.title)),
    ),
    extractProjectTasks(activeRoadmap),
  );
  const evidenceSummary =
    activeRoadmap?.evidence_summary ?? analysisResult?.evidence_summary ?? [];
  const skillDiagnostics =
    activeRoadmap?.skill_diagnostics ?? analysisResult?.skill_diagnostics ?? [];
  const demonstratedSkills = skillDiagnostics.filter((skill) => skill.current_level > 0);
  const priorityGaps = skillDiagnostics.filter((skill) => skill.current_level < 5);
  const cycles = activeRoadmap?.cycles ?? analysisResult?.cycles ?? [];
  const projectBlueprints =
    activeRoadmap?.project_blueprints ?? analysisResult?.project_blueprints ?? [];
  const interestDomain =
    activeRoadmap?.interest_domain ?? analysisResult?.interest_domain ?? "-";
  const fitScore = getDisplayFitScore(analysisResult, activeRoadmap, hasRoadmap);
  const capabilityScore = activeRoadmap?.capability_score ?? analysisResult?.capability_score ?? 0;
  const projectEvidenceScore =
    activeRoadmap?.project_evidence_score ?? analysisResult?.project_evidence_score ?? 0;
  const applicationReadinessScore =
    activeRoadmap?.application_readiness_score ??
    analysisResult?.application_readiness_score ??
    0;
  const summary =
    translateSummary(analysisResult?.summary ?? analysisResult?.impact) ??
    `${targetRole} 준비를 위한 분석이 완료되었습니다. 보완할 기술과 주차별 로드맵을 확인해보세요.`;
  const progressPercent = activeRoadmap?.progress_percent ?? analysisResult?.progress_percent ?? 0;

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[commonStyles.card, styles.heroCard]}>
        <Text style={styles.heroLabel}>12주 취업 준비 달성률</Text>
        <Text style={[styles.heroTitle, { fontSize: isSmallScreen ? 22 : 25 }]}>
          {targetRole}
        </Text>
        <Text style={[styles.heroScore, { fontSize: isSmallScreen ? 38 : 44 }]}>
          {fitScore}%
        </Text>
        <Text style={styles.scoreExplanation}>
          목표 직무에 지원하기 위해 필요한 기술 연습, 프로젝트 증명, 서류/면접 준비 중
          현재 완료를 증명한 비율입니다.
        </Text>
        <Text style={styles.goalMessage}>
          12주 안에 100%를 달성해, 지원할 수 있는 포트폴리오와 준비 근거를 완성해보세요.
        </Text>
        <Text style={styles.heroSubText}>{summary}</Text>
      </View>

      <FieldCard title="목표 직무" value={targetRole} isSmallScreen={isSmallScreen} />
      <FieldCard title="관심 소재" value={interestDomain} isSmallScreen={isSmallScreen} />
      <FieldCard title="12주 취업 준비 달성률" value={`${fitScore}%`} isSmallScreen={isSmallScreen} />
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          기준선 구성
        </Text>
        <ScoreRow label="기술 수행 체크리스트" score={capabilityScore} maximum={60} />
        <ScoreRow label="프로젝트 증명도" score={projectEvidenceScore} maximum={25} />
        <ScoreRow label="지원 서류/면접 준비" score={applicationReadinessScore} maximum={15} />
        <Text style={commonStyles.bodyText}>
          100%는 취업 성공 확률이 아니라, 목표 직무 지원에 필요한 준비를 증명 가능한
          결과물과 행동으로 완료했다는 기준입니다.
        </Text>
      </View>
      {(activeRoadmap?.reassessments ?? []).length > 0 && (
        <View style={[commonStyles.card, styles.updatedCard]}>
          <Text style={styles.updatedTitle}>진행 결과가 반영되었습니다</Text>
          <Text style={commonStyles.bodyText}>
            {(activeRoadmap.reassessments ?? [])
              .map((item) => `${item.checkpoint_week}주차 ${item.capability_score_before}점 -> ${item.capability_score_after}점`)
              .join(" / ")}
          </Text>
        </View>
      )}
      {skillDiagnostics.length ? (
        <>
          <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
            <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
              현재 역량 진단
            </Text>
            {demonstratedSkills.length ? (
              demonstratedSkills.map((diagnostic) => (
                <CapabilityRow diagnostic={diagnostic} key={diagnostic.skill} />
              ))
            ) : (
              <Text style={commonStyles.bodyText}>
                체크리스트에서 수행 경험이 확인된 기술이 없습니다. 우선순위가 높은 기술부터 프로젝트 안에서 익히도록 구성했습니다.
              </Text>
            )}
          </View>
          <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
            <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
              보완 우선순위
            </Text>
            {priorityGaps.map((diagnostic, index) => (
              <PriorityGapRow diagnostic={diagnostic} index={index} key={diagnostic.skill} />
            ))}
          </View>
          <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
            <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
              추천 학습 실행안
            </Text>
            {cycles.map((cycle, index) => (
              <LearningCycle
                cycle={cycle}
                diagnostics={skillDiagnostics}
                index={index}
                key={`${cycle.title}-${index}`}
              />
            ))}
          </View>
        </>
      ) : (
        <>
          <ListCard title="현재 보유 기술" items={currentSkills} isSmallScreen={isSmallScreen} />
          <ListCard title="보완할 기술" items={missingSkills} isSmallScreen={isSmallScreen} />
          <ListCard title="추천 학습" items={recommendedLearning} isSmallScreen={isSmallScreen} />
        </>
      )}
      {targetRole === "Data Scientist" && certificationOptions.length > 0 && (
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <View style={styles.betaHeader}>
            <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
              선택형 준비 항목
            </Text>
            <Text style={styles.betaBadge}>BETA</Text>
          </View>
          <Text style={commonStyles.bodyText}>
            자격증은 필수가 아니며 현재 점수에는 반영하지 않습니다. 데이터 분석 기초를 정리할 보조 일정으로 선택할 수 있습니다.
          </Text>
          {certificationOptions.map((option) => (
            <View key={option.code} style={styles.certificationBlock}>
              <Text style={styles.certificateTitle}>{option.name} {option.round}</Text>
              <Text style={commonStyles.bodyText}>{option.fit_reason}</Text>
              <Text style={styles.dateText}>
                접수 {formatDate(option.registration_start)} - {formatDate(option.registration_end)}
              </Text>
              <Text style={styles.dateText}>
                시험 {formatDate(option.exam_date)} / 권장 시작 {formatDate(option.recommended_start_date)}
              </Text>
              <Pressable
                disabled={option.is_selected || pendingCertification === option.code}
                onPress={() => includeCertification(option.code)}
                style={[
                  styles.addCertificationButton,
                  option.is_selected && styles.selectedCertificationButton,
                ]}
              >
                <Text style={styles.addCertificationText}>
                  {option.is_selected ? "로드맵에 추가됨" : "4주 준비 계획 추가"}
                </Text>
              </Pressable>
            </View>
          ))}
          {!!certificationError && (
            <Text style={commonStyles.errorText}>{certificationError}</Text>
          )}
          <Pressable onPress={() => Linking.openURL(certificationOptions[0].official_url)}>
            <Text style={styles.officialLink}>K-DATA 공식 시험 일정 확인</Text>
          </Pressable>
        </View>
      )}
      {projectBlueprints.length ? (
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
            직무 근거 기반 추천 프로젝트
          </Text>
          {projectBlueprints.map((blueprint, index) => (
            <ProjectBlueprint blueprint={blueprint} index={index} key={blueprint.title} />
          ))}
          <Pressable
            style={[commonStyles.primaryButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Assignment")}
          >
            <Text style={commonStyles.primaryButtonText}>과제 제출 및 AI 평가로 이동</Text>
          </Pressable>
        </View>
      ) : (
        <ListCard
          title="추천 프로젝트"
          items={recommendedProjects}
          isSmallScreen={isSmallScreen}
          chipStyle={styles.projectChip}
          chipTextStyle={styles.projectChipText}
        />
      )}
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          추천 근거
        </Text>
        {evidenceSummary.length ? (
          evidenceSummary.map((evidence) => (
            <Text key={evidence.skill} style={commonStyles.bodyText}>
              {evidence.skill}: {evidence.evidence_company_count}개 회사, 직접 확인 공고{" "}
              {evidence.keyword_posting_count}건 ({evidence.evidence_level})
            </Text>
          ))
        ) : (
          <Text style={commonStyles.bodyText}>확인 가능한 시장 근거가 아직 부족합니다.</Text>
        )}
      </View>
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          12주 프로젝트 구성
        </Text>
        {cycles.map((cycle, index) => (
          <View key={`${cycle.title}-${index}`} style={{ gap: 4, marginBottom: 10 }}>
            <Text style={styles.cycleTitle}>
              {index + 1}사이클: {cycle.title}
            </Text>
            <Text style={commonStyles.bodyText}>{cycle.project}</Text>
            <Text style={commonStyles.bodyText}>집중 역량: {(cycle.skills ?? []).join(", ")}</Text>
            <Text style={styles.signalText}>실무 신호: {cycle.signal}</Text>
          </View>
        ))}
      </View>
      <FieldCard title="요약" value={summary} isSmallScreen={isSmallScreen} />

      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          로드맵 요약
        </Text>
        <Text style={commonStyles.bodyText}>
          현재 진행률은 {progressPercent}%입니다. 주차별 계획은 로드맵 화면에서 확인할 수 있습니다.
        </Text>
      </View>

      <Pressable
        style={[commonStyles.secondaryButton, isSmallScreen && commonStyles.compactButton]}
        onPress={() => navigation.navigate("Calendar")}
      >
        <Text style={commonStyles.secondaryButtonText}>로드맵 보기</Text>
      </Pressable>
    </ScrollView>
  );
}

function FieldCard({ title, value, isSmallScreen }) {
  return (
    <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
      <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
        {title}
      </Text>
      <Text style={commonStyles.bodyText}>{value || "-"}</Text>
    </View>
  );
}

function ListCard({ title, items, isSmallScreen, chipStyle, chipTextStyle }) {
  return (
    <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
      <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
        {title}
      </Text>
      {items.length ? (
        <View style={commonStyles.chipWrap}>
          {items.map((item, index) => (
            <View key={`item-${item}-${index}`} style={[commonStyles.chip, chipStyle]}>
              <Text style={[styles.chipText, chipTextStyle]}>{item}</Text>
            </View>
          ))}
        </View>
      ) : (
        <Text style={commonStyles.bodyText}>-</Text>
      )}
    </View>
  );
}

function ScoreRow({ label, score, maximum }) {
  return (
    <View style={styles.scoreRow}>
      <Text style={styles.scoreLabel}>{label}</Text>
      <Text style={styles.scoreValue}>{score} / {maximum}</Text>
    </View>
  );
}

function CapabilityRow({ diagnostic }) {
  return (
    <View style={styles.diagnosticRow}>
      <View style={styles.diagnosticHeader}>
        <Text style={styles.diagnosticSkill}>{diagnostic.skill}</Text>
        <Text style={styles.levelPill}>
          {diagnostic.current_level}/5 {diagnostic.level_label}
        </Text>
      </View>
      <Text style={styles.actionText}>{diagnostic.recommended_action}</Text>
    </View>
  );
}

function PriorityGapRow({ diagnostic, index }) {
  return (
    <View style={styles.diagnosticRow}>
      <View style={styles.diagnosticHeader}>
        <Text style={styles.priorityTitle}>{index + 1}. {diagnostic.skill}</Text>
        <Text style={styles.priorityPill}>{diagnostic.status}</Text>
      </View>
      <Text style={styles.marketText}>
        현재 {diagnostic.level_label} / 수요 근거 {Math.round(diagnostic.market_score)}점
      </Text>
      <Text style={commonStyles.bodyText}>{diagnostic.evidence_reason}</Text>
      <Text style={styles.actionText}>다음 행동: {diagnostic.recommended_action}</Text>
    </View>
  );
}

function LearningCycle({ cycle, diagnostics, index }) {
  const actions = (cycle.skills ?? [])
    .map((skill) => diagnostics.find((diagnostic) => diagnostic.skill === skill))
    .filter(Boolean);

  return (
    <View style={styles.learningCycle}>
      <Text style={styles.cycleTitle}>{index + 1}사이클: {cycle.project}</Text>
      {actions.map((diagnostic) => (
        <Text key={diagnostic.skill} style={styles.learningAction}>
          {diagnostic.skill}: {diagnostic.recommended_action}
        </Text>
      ))}
      <Text style={styles.signalText}>결과 증명: {cycle.signal}</Text>
    </View>
  );
}

function ProjectBlueprint({ blueprint, index }) {
  return (
    <View style={styles.projectBlueprint}>
      <Text style={styles.blueprintCycle}>{index + 1}사이클 프로젝트</Text>
      <Text style={styles.blueprintTitle}>{blueprint.title}</Text>
      <Text style={commonStyles.bodyText}>{blueprint.problem}</Text>
      <BlueprintSection title="추천 근거" items={[blueprint.recommendation_basis]} />
      <BlueprintSection title="구성 원칙" items={[blueprint.method_basis]} />
      <BlueprintSection title="관심 소재 적용 예시" items={[blueprint.domain_example]} />
      <BlueprintSection title="예시 데이터" items={[blueprint.data_plan]} />
      <BlueprintSection title="구현 기술 및 모델" items={blueprint.techniques} />
      <BlueprintSection title="평가 기준" items={blueprint.evaluation} />
      <BlueprintSection title="완성 산출물" items={blueprint.deliverables} />
      <BlueprintSection title="검증 체크리스트" items={blueprint.validation_rubric} />
    </View>
  );
}

function BlueprintSection({ title, items }) {
  return (
    <View style={styles.blueprintSection}>
      <Text style={styles.blueprintLabel}>{title}</Text>
      {(items ?? []).map((item) => (
        <Text key={`${title}-${item}`} style={styles.blueprintItem}>- {item}</Text>
      ))}
    </View>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${year}.${month}.${day}`;
}

function getDisplayFitScore(analysisResult, activeRoadmap, hasRoadmap) {
  if (typeof activeRoadmap?.readiness_score === "number") {
    return Math.round(activeRoadmap.readiness_score);
  }
  if (typeof analysisResult?.readiness_score === "number") {
    return Math.round(analysisResult.readiness_score);
  }
  return getBaseFitScore(analysisResult, hasRoadmap);
}

function getBaseFitScore(analysisResult, hasRoadmap) {
  if (typeof analysisResult?.fit_score === "number" && analysisResult.fit_score > 0) {
    return Math.round(analysisResult.fit_score);
  }
  if (typeof analysisResult?.demand_probability === "number") {
    return Math.round(analysisResult.demand_probability * 100);
  }
  return hasRoadmap ? 30 : 0;
}

function extractRoadmapLearning(activeRoadmap) {
  return unique(
    (activeRoadmap?.weeks ?? [])
      .flatMap((week) => week.tasks ?? [])
      .filter((task) => task.task_type === "study")
      .map((task) => stripLearningSuffix(task.task_title)),
  ).slice(0, 8);
}

function extractProjectTasks(activeRoadmap) {
  const projects = unique(
    (activeRoadmap?.weeks ?? [])
      .flatMap((week) => week.tasks ?? [])
      .filter((task) => task.task_type === "project" || task.task_type === "portfolio")
      .map((task) => task.task_title),
  );
  return projects.length ? projects : ["직무 프로젝트 1개 완성", "포트폴리오 정리"];
}

function stripLearningSuffix(value) {
  return String(value)
    .replace(" 학습 및 실습", "")
    .replace(" 기초 학습", "")
    .trim();
}

function withFallback(primary, fallback) {
  return primary.length ? primary : toArray(fallback);
}

function includesIgnoreCase(items, value) {
  const target = String(value).toLowerCase();
  return items.some((item) => String(item).toLowerCase() === target);
}

function unique(items) {
  const seen = new Set();
  const result = [];
  for (const item of toArray(items)) {
    const trimmed = String(item).trim();
    const key = trimmed.toLowerCase();
    if (!trimmed || seen.has(key)) continue;
    seen.add(key);
    result.push(trimmed);
  }
  return result;
}

function toArray(value) {
  if (!value) return [];
  if (Array.isArray(value)) {
    return uniqueFlat(value);
  }
  return [String(value)].filter(Boolean);
}

function uniqueFlat(items) {
  const result = [];
  for (const item of items.flat(Infinity)) {
    if (item) result.push(String(item));
  }
  return result;
}

function translateSummary(value) {
  if (!value) return null;
  if (value === "낮음" || value === "low") {
    return "시장 수요는 아직 낮게 평가되지만, 핵심 역량을 쌓으면 충분히 준비할 수 있습니다.";
  }
  if (value === "보통" || value === "medium") {
    return "시장 수요가 안정적인 편입니다. 부족한 기술을 보완하며 프로젝트 경험을 쌓아보세요.";
  }
  if (value === "높음" || value === "high") {
    return "시장 수요가 높은 편입니다. 실무형 프로젝트와 포트폴리오 정리에 집중해보세요.";
  }
  return String(value)
    .replace("Career-path analysis is ready.", "커리어 분석이 완료되었습니다.")
    .replace("needs", "준비에는")
    .replace("focused learning and project preparation.", "중심의 학습과 프로젝트 준비가 필요합니다.");
}

function translateProjectTitle(value) {
  const titleMap = {
    "Build core skills": "핵심 기술 기초 다지기",
    "Apply AI skills": "AI 기술 적용하기",
    "Practice agent workflows": "에이전트 워크플로우 실습하기",
  };
  return titleMap[value] ?? value;
}

function screenPadding(contentBottomPadding, isSmallScreen) {
  return [
    commonStyles.screen,
    {
      paddingBottom: contentBottomPadding,
      paddingHorizontal: isSmallScreen ? 14 : 20,
      paddingTop: isSmallScreen ? 14 : 20,
    },
  ];
}

const styles = {
  heroCard: {
    backgroundColor: "#1F6F68",
  },
  heroLabel: {
    color: "#C9F0DF",
    fontSize: 13,
    fontWeight: "900",
  },
  heroTitle: {
    color: "#FFFFFF",
    fontWeight: "900",
    lineHeight: 31,
  },
  heroScore: {
    color: "#FFFFFF",
    fontWeight: "900",
  },
  scoreExplanation: {
    color: "#C9F0DF",
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 19,
  },
  goalMessage: {
    backgroundColor: "#D9EEE5",
    borderRadius: 8,
    color: "#17483E",
    fontSize: 13,
    fontWeight: "900",
    lineHeight: 19,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  heroSubText: {
    color: "#D9EEE5",
    fontSize: 14,
    fontWeight: "800",
  },
  chipText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "900",
  },
  projectChip: {
    backgroundColor: colors.greenSoft,
    borderColor: "#BFD8CB",
    borderRadius: 12,
    borderWidth: 1,
  },
  projectChipText: {
    color: colors.green,
  },
  cycleTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  signalText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "800",
    lineHeight: 19,
  },
  scoreRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  scoreLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "800",
  },
  scoreValue: {
    color: colors.green,
    fontSize: 15,
    fontWeight: "900",
  },
  betaHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  betaBadge: {
    backgroundColor: "#E7F2EE",
    borderRadius: 6,
    color: colors.green,
    fontSize: 11,
    fontWeight: "900",
    paddingHorizontal: 7,
    paddingVertical: 4,
  },
  certificationBlock: {
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 8,
    borderWidth: 1,
    gap: 7,
    padding: 12,
  },
  certificateTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  dateText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "800",
  },
  addCertificationButton: {
    alignItems: "center",
    backgroundColor: colors.green,
    borderRadius: 8,
    minHeight: 42,
    justifyContent: "center",
    marginTop: 4,
  },
  selectedCertificationButton: {
    backgroundColor: "#617169",
  },
  addCertificationText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "900",
  },
  officialLink: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
    textDecorationLine: "underline",
  },
  diagnosticRow: {
    borderTopColor: "#E3DACD",
    borderTopWidth: 1,
    gap: 6,
    paddingTop: 11,
  },
  diagnosticHeader: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    justifyContent: "space-between",
  },
  diagnosticSkill: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  levelPill: {
    backgroundColor: colors.greenSoft,
    borderRadius: 6,
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  priorityTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  priorityPill: {
    backgroundColor: "#17212B",
    borderRadius: 6,
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "900",
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  marketText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  actionText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 20,
  },
  learningCycle: {
    borderTopColor: "#E3DACD",
    borderTopWidth: 1,
    gap: 7,
    paddingTop: 11,
  },
  learningAction: {
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
  },
  projectBlueprint: {
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 8,
    borderWidth: 1,
    gap: 9,
    padding: 13,
  },
  blueprintCycle: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  blueprintTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
    lineHeight: 23,
  },
  blueprintSection: {
    gap: 4,
  },
  blueprintLabel: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  blueprintItem: {
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
  },
  updatedCard: {
    backgroundColor: "#F0F7F3",
    borderColor: "#BFD8CB",
    borderRadius: 8,
  },
  updatedTitle: {
    color: colors.green,
    fontSize: 16,
    fontWeight: "900",
  },
};
