import { Pressable, ScrollView, Text, View } from "react-native";

import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

const TEST_FIT_SCORE = 70;

export default function ResultScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, analysisResult, lastSkills } = useAnalysis();
  const hasResult = !!analysisResult;
  const hasRoadmap = !!activeRoadmap?.id;

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

  const targetRole =
    analysisResult?.target_role ??
    analysisResult?.future_job ??
    analysisResult?.job_target ??
    activeRoadmap?.job_target ??
    "-";
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
  const fitScore = getDisplayFitScore(analysisResult, hasRoadmap);
  const summary =
    translateSummary(analysisResult?.summary ?? analysisResult?.impact) ??
    `${targetRole} 준비를 위한 분석이 완료되었습니다. 보완할 기술과 주차별 로드맵을 확인해보세요.`;
  const progressPercent = activeRoadmap?.progress_percent ?? analysisResult?.progress_percent ?? 0;

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[commonStyles.card, styles.heroCard]}>
        <Text style={styles.heroLabel}>목표 직무 적합도</Text>
        <Text style={[styles.heroTitle, { fontSize: isSmallScreen ? 22 : 25 }]}>
          {targetRole}
        </Text>
        <Text style={[styles.heroScore, { fontSize: isSmallScreen ? 38 : 44 }]}>
          {fitScore}%
        </Text>
        <Text style={styles.heroSubText}>{summary}</Text>
      </View>

      <FieldCard title="목표 직무" value={targetRole} isSmallScreen={isSmallScreen} />
      <FieldCard title="적합도" value={`${fitScore}%`} isSmallScreen={isSmallScreen} />
      <ListCard title="현재 보유 기술" items={currentSkills} isSmallScreen={isSmallScreen} />
      <ListCard title="보완할 기술" items={missingSkills} isSmallScreen={isSmallScreen} />
      <ListCard title="추천 학습" items={recommendedLearning} isSmallScreen={isSmallScreen} />
      <ListCard
        title="추천 프로젝트"
        items={recommendedProjects}
        isSmallScreen={isSmallScreen}
        chipStyle={styles.projectChip}
        chipTextStyle={styles.projectChipText}
      />
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

function getDisplayFitScore(analysisResult, hasRoadmap) {
  return TEST_FIT_SCORE;
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
};
