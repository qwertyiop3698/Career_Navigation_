import { useEffect } from "react";
import { ArrowRight, CalendarDays, ClipboardCheck, RefreshCw, Search } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";

import { getMyRoadmap } from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function HomeScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, analysisResult, setActiveRoadmap } = useAnalysis();
  const roadmap = activeRoadmap;
  const hasRoadmap = !!roadmap?.id;
  const diagnostics = roadmap?.skill_diagnostics ?? analysisResult?.skill_diagnostics ?? [];
  const priorityGaps = diagnostics.filter((skill) => skill.current_level < 5).slice(0, 2);
  const readinessScore = Math.round(
    roadmap?.readiness_score ?? analysisResult?.readiness_score ?? 0,
  );
  const capabilityScore = roadmap?.capability_score ?? analysisResult?.capability_score ?? 0;
  const projectScore =
    roadmap?.project_evidence_score ?? analysisResult?.project_evidence_score ?? 0;
  const applicationScore =
    roadmap?.application_readiness_score ??
    analysisResult?.application_readiness_score ??
    0;
  const nextTask = findNextTask(roadmap);

  useEffect(() => {
    let isMounted = true;
    getMyRoadmap()
      .then((data) => {
        if (isMounted && data?.roadmap) {
          setActiveRoadmap(data.roadmap);
        }
      })
      .catch((error) => {
        console.error("[Roadmap] failed to load active roadmap", {
          data: error.response?.data,
          status: error.response?.status,
          message: error.message,
        });
      });
    return () => {
      isMounted = false;
    };
  }, [setActiveRoadmap]);

  if (!hasRoadmap) {
    return (
      <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
            12주 취업 준비를 시작하세요
          </Text>
          <Text style={commonStyles.bodyText}>
            목표 직무와 현재 기술을 입력하면 필요한 준비와 프로젝트를 정리해드립니다.
          </Text>
          <Pressable
            style={[
              commonStyles.primaryButton,
              styles.beginButton,
              isSmallScreen && commonStyles.compactButton,
            ]}
            onPress={() => navigation.navigate("Input")}
          >
            <Text style={commonStyles.primaryButtonText}>새로 분석하기</Text>
            <ArrowRight color="#FFFFFF" size={18} />
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[styles.hero, isSmallScreen && styles.compactHero]}>
        <View style={styles.heroHeader}>
          <View style={styles.heroCopy}>
            <Text style={styles.eyebrow}>12주 취업 준비 달성률</Text>
            <Text numberOfLines={2} style={[styles.targetRole, isSmallScreen && styles.compactRole]}>
              {roadmap.job_target}
            </Text>
          </View>
          <Text style={[styles.score, isSmallScreen && styles.compactScore]}>{readinessScore}%</Text>
        </View>
        <View style={styles.track}>
          <View style={[styles.trackFill, { width: `${readinessScore}%` }]} />
        </View>
        <Text style={styles.scoreCaption}>
          준비 근거를 완성해 12주 안에 100% 달성을 목표로 합니다.
        </Text>
      </View>

      <View style={styles.metricRow}>
        <Metric label="기술" score={capabilityScore} maximum={60} />
        <Metric label="프로젝트" score={projectScore} maximum={25} />
        <Metric label="지원 준비" score={applicationScore} maximum={15} />
      </View>

      <View style={[styles.focusPanel, isSmallScreen && styles.compactPanel]}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>지금 집중할 것</Text>
          <Pressable onPress={() => navigation.navigate("Result")}>
            <Text style={styles.detailLink}>근거 보기</Text>
          </Pressable>
        </View>
        {priorityGaps.length ? (
          priorityGaps.map((skill, index) => (
            <View key={skill.skill} style={styles.focusRow}>
              <Text style={styles.rank}>{index + 1}</Text>
              <View style={styles.focusCopy}>
                <Text style={styles.focusSkill}>{skill.skill}</Text>
                <Text numberOfLines={1} style={styles.focusReason}>
                  {skill.evidence_company_count}개 회사 공고 근거 / {skill.status}
                </Text>
              </View>
            </View>
          ))
        ) : (
          <Text style={styles.emptyFocus}>우선 보완 기술이 없습니다. 프로젝트 증명을 진행하세요.</Text>
        )}
        {!!nextTask && (
          <View style={styles.nextAction}>
            <Text style={styles.nextLabel}>다음 할 일</Text>
            <Text numberOfLines={1} style={styles.nextTask}>{nextTask}</Text>
          </View>
        )}
      </View>

      <View style={styles.actionGrid}>
        <QuickAction
          icon={CalendarDays}
          label="로드맵"
          onPress={() => navigation.navigate("Calendar")}
          primary
        />
        <QuickAction
          icon={ClipboardCheck}
          label="과제 검증"
          onPress={() => navigation.navigate("Assignment")}
        />
        <QuickAction icon={Search} label="상세 결과" onPress={() => navigation.navigate("Result")} />
        <QuickAction icon={RefreshCw} label="재분석" onPress={() => navigation.navigate("Input")} />
      </View>
    </ScrollView>
  );
}

function Metric({ label, score, maximum }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{score}</Text>
      <Text style={styles.metricMax}>/ {maximum}</Text>
    </View>
  );
}

function QuickAction({ icon: Icon, label, onPress, primary = false }) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.quickAction, primary && styles.primaryQuickAction]}
    >
      <Icon color={primary ? "#FFFFFF" : colors.green} size={19} strokeWidth={2.4} />
      <Text style={[styles.quickActionText, primary && styles.primaryQuickText]}>{label}</Text>
    </Pressable>
  );
}

function findNextTask(roadmap) {
  return (roadmap?.weeks ?? [])
    .flatMap((week) => week.tasks ?? [])
    .find((task) => !task.is_completed)?.task_title;
}

function screenPadding(contentBottomPadding, isSmallScreen) {
  return [
    styles.screen,
    {
      gap: isSmallScreen ? 10 : 12,
      paddingBottom: contentBottomPadding,
      paddingHorizontal: isSmallScreen ? 14 : 20,
      paddingTop: isSmallScreen ? 12 : 16,
    },
  ];
}

const styles = {
  screen: {
    flexGrow: 1,
  },
  beginButton: {
    flexDirection: "row",
    gap: 8,
  },
  hero: {
    backgroundColor: "#1F6F68",
    borderRadius: 8,
    gap: 11,
    padding: 17,
  },
  compactHero: {
    gap: 8,
    padding: 14,
  },
  heroHeader: {
    alignItems: "flex-end",
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  heroCopy: {
    flex: 1,
    gap: 5,
  },
  eyebrow: {
    color: "#C9F0DF",
    fontSize: 12,
    fontWeight: "900",
  },
  targetRole: {
    color: "#FFFFFF",
    fontSize: 21,
    fontWeight: "900",
    lineHeight: 26,
  },
  compactRole: {
    fontSize: 18,
    lineHeight: 23,
  },
  score: {
    color: "#FFFFFF",
    fontSize: 39,
    fontWeight: "900",
  },
  compactScore: {
    fontSize: 34,
  },
  track: {
    backgroundColor: "#438881",
    borderRadius: 6,
    height: 8,
    overflow: "hidden",
  },
  trackFill: {
    backgroundColor: "#D9EEE5",
    borderRadius: 6,
    height: 8,
  },
  scoreCaption: {
    color: "#D9EEE5",
    fontSize: 12,
    fontWeight: "700",
    lineHeight: 17,
  },
  metricRow: {
    flexDirection: "row",
    gap: 8,
  },
  metric: {
    backgroundColor: "#FFFDF8",
    borderColor: colors.cardBorder,
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  metricLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "900",
  },
  metricValue: {
    color: colors.green,
    fontSize: 21,
    fontWeight: "900",
    marginTop: 3,
  },
  metricMax: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "800",
  },
  focusPanel: {
    backgroundColor: "#FFFDF8",
    borderColor: colors.cardBorder,
    borderRadius: 8,
    borderWidth: 1,
    gap: 10,
    padding: 14,
  },
  compactPanel: {
    gap: 8,
    padding: 12,
  },
  sectionHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  detailLink: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  focusRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  rank: {
    backgroundColor: colors.greenSoft,
    borderRadius: 6,
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 9,
    paddingVertical: 7,
  },
  focusCopy: {
    flex: 1,
    gap: 2,
  },
  focusSkill: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  focusReason: {
    color: colors.muted,
    fontSize: 12,
    lineHeight: 17,
  },
  emptyFocus: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 19,
  },
  nextAction: {
    alignItems: "center",
    backgroundColor: colors.greenSoft,
    borderRadius: 7,
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  nextLabel: {
    color: colors.green,
    fontSize: 11,
    fontWeight: "900",
  },
  nextTask: {
    color: colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: "800",
  },
  actionGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  quickAction: {
    alignItems: "center",
    backgroundColor: "#FFFDF8",
    borderColor: colors.cardBorder,
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: "48%",
    flexDirection: "row",
    flexGrow: 1,
    gap: 7,
    justifyContent: "center",
    minHeight: 46,
    paddingHorizontal: 10,
  },
  primaryQuickAction: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  quickActionText: {
    color: colors.green,
    fontSize: 14,
    fontWeight: "900",
  },
  primaryQuickText: {
    color: "#FFFFFF",
  },
};
