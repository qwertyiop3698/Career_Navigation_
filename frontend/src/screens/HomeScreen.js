import { useEffect } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { getMyRoadmap } from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function HomeScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, analysisResult, lastSkills, setActiveRoadmap } = useAnalysis();
  const roadmap = activeRoadmap;
  const hasRoadmap = !!roadmap?.id;
  const prioritySkills = (analysisResult?.recommended_skills?.length
    ? analysisResult.recommended_skills
    : lastSkills
  ).slice(0, 3);

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

  return (
    <ScrollView
      contentContainerStyle={[
        commonStyles.screen,
        {
          paddingBottom: contentBottomPadding,
          paddingHorizontal: isSmallScreen ? 14 : 20,
          paddingTop: isSmallScreen ? 14 : 20,
        },
      ]}
    >
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          오늘의 취업 준비
        </Text>
        {!hasRoadmap ? (
          <>
            <Text style={commonStyles.bodyText}>
              아직 로드맵이 없습니다. 새로 분석을 시작해보세요.
            </Text>
            <Pressable
              style={[commonStyles.primaryButton, isSmallScreen && commonStyles.compactButton]}
              onPress={() => navigation.navigate("Input")}
            >
              <Text style={commonStyles.primaryButtonText}>새로 분석하기</Text>
            </Pressable>
          </>
        ) : (
          <>
            <View style={styles.summaryRow}>
              <SummaryItem label="목표 직무" value={roadmap.job_target} />
              <SummaryItem label="진행률" value={`${roadmap.progress_percent ?? 0}%`} />
            </View>
            <View style={styles.progressBox}>
              <Text style={styles.progressLabel}>12주 로드맵 진행률</Text>
              <Text style={styles.progressValue}>{roadmap.progress_percent ?? 0}%</Text>
              <Text style={commonStyles.bodyText}>
                총 {roadmap.weeks?.length ?? 0}주 계획이 준비되어 있습니다. 오늘 체크할 수 있는 항목부터 완료해보세요.
              </Text>
            </View>
            <Text style={styles.sectionLabel}>우선 학습 기술</Text>
            <View style={commonStyles.chipWrap}>
              {prioritySkills.map((skill, index) => (
                <Text key={`skill-${skill}-${index}`} style={commonStyles.chip}>
                  {skill}
                </Text>
              ))}
            </View>
          </>
        )}
      </View>

      {hasRoadmap && (
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Pressable
            style={[commonStyles.primaryButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Result")}
          >
            <Text style={commonStyles.primaryButtonText}>결과 자세히 보기</Text>
          </Pressable>
          <Pressable
            style={[commonStyles.secondaryButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Calendar")}
          >
            <Text style={commonStyles.secondaryButtonText}>로드맵 보기</Text>
          </Pressable>
          <Pressable
            style={[commonStyles.lightButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Assignment")}
          >
            <Text style={commonStyles.lightButtonText}>과제 제출 및 평가</Text>
          </Pressable>
          <Pressable
            style={[commonStyles.lightButton, isSmallScreen && commonStyles.compactButton]}
            onPress={() => navigation.navigate("Input")}
          >
            <Text style={commonStyles.lightButtonText}>새로 분석하기</Text>
          </Pressable>
        </View>
      )}
    </ScrollView>
  );
}

function SummaryItem({ label, value }) {
  return (
    <View style={styles.summaryItem}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text numberOfLines={2} style={styles.summaryValue}>
        {value || "-"}
      </Text>
    </View>
  );
}

const styles = {
  summaryRow: {
    flexDirection: "row",
    gap: 10,
  },
  summaryItem: {
    backgroundColor: colors.greenSoft,
    borderRadius: 18,
    flex: 1,
    gap: 6,
    padding: 12,
  },
  summaryLabel: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  summaryValue: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "900",
    lineHeight: 22,
  },
  progressBox: {
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 18,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  progressLabel: {
    color: colors.muted,
    fontSize: 13,
    fontWeight: "900",
  },
  progressValue: {
    color: colors.green,
    fontSize: 28,
    fontWeight: "900",
  },
  sectionLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
};
