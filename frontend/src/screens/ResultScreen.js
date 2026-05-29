import { Pressable, ScrollView, Text, View } from "react-native";

import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function ResultScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, analysisResult, lastSkills } = useAnalysis();
  const hasResult = !!analysisResult;
  const hasRoadmap = !!activeRoadmap?.id;
  const targetRole =
    analysisResult?.target_role ??
    analysisResult?.future_job ??
    analysisResult?.job_target ??
    activeRoadmap?.job_target ??
    "-";
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
  const projectBlueprints =
    activeRoadmap?.project_blueprints ?? analysisResult?.project_blueprints ?? [];
  const interestDomain =
    activeRoadmap?.interest_domain ?? analysisResult?.interest_domain ?? "-";

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[styles.detailHeader, isSmallScreen && styles.compactDetailHeader]}>
        <Text style={styles.detailEyebrow}>분석 상세</Text>
        <Text style={[styles.detailTitle, isSmallScreen && styles.compactDetailTitle]}>
          {targetRole}
        </Text>
        <Text style={styles.detailMeta}>관심 소재: {interestDomain}</Text>
        <Text style={styles.detailDescription}>
          채용공고에서 확인된 기술 근거와 현재 수행 수준을 기준으로 추천 이유를 보여드립니다.
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
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          채용공고 기반 근거
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
        </>
      ) : (
        <>
          <ListCard title="현재 보유 기술" items={currentSkills} isSmallScreen={isSmallScreen} />
          <ListCard title="보완할 기술" items={missingSkills} isSmallScreen={isSmallScreen} />
          <ListCard title="추천 학습" items={recommendedLearning} isSmallScreen={isSmallScreen} />
        </>
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

      <Pressable
        style={[commonStyles.secondaryButton, isSmallScreen && commonStyles.compactButton]}
        onPress={() => navigation.navigate("Calendar")}
      >
        <Text style={commonStyles.secondaryButtonText}>로드맵 보기</Text>
      </Pressable>
    </ScrollView>
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
  detailHeader: {
    backgroundColor: "#FFFDF8",
    borderBottomColor: colors.cardBorder,
    borderBottomWidth: 1,
    gap: 7,
    paddingBottom: 15,
  },
  compactDetailHeader: {
    paddingBottom: 12,
  },
  detailEyebrow: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  detailTitle: {
    color: colors.text,
    fontSize: 25,
    fontWeight: "900",
    lineHeight: 31,
  },
  compactDetailTitle: {
    fontSize: 22,
    lineHeight: 28,
  },
  detailMeta: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  detailDescription: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 21,
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
