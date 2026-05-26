import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { getMe, getMyRoadmap, getMyRoadmapProgress, updateGithubProfile } from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../navigation/AuthContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function ProfileScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
}) {
  const { signOut } = useAuth();
  const { activeRoadmap, setActiveRoadmap } = useAnalysis();
  const [user, setUser] = useState(null);
  const [progress, setProgress] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [isSavingGithub, setIsSavingGithub] = useState(false);
  const [githubMessage, setGithubMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      setError("");
      setIsLoading(true);
      try {
        const [me, roadmapData, progressData] = await Promise.all([
          getMe(),
          getMyRoadmap(),
          getMyRoadmapProgress(),
        ]);
        if (!isMounted) return;
        setUser(me);
        setGithubUrl(me.github_url ?? "");
        setProgress(progressData);
        if (roadmapData?.roadmap) {
          setActiveRoadmap(roadmapData.roadmap);
        }
      } catch (requestError) {
        if (!isMounted) return;
        const detail = requestError.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "내 정보를 불러오지 못했습니다.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadProfile();
    return () => {
      isMounted = false;
    };
  }, [setActiveRoadmap]);

  const saveGithubUrl = async () => {
    setIsSavingGithub(true);
    setGithubMessage("");
    setError("");
    try {
      const result = await updateGithubProfile({ github_url: githubUrl.trim() || null });
      setGithubUrl(result.github_url ?? "");
      setUser((current) => ({ ...current, github_url: result.github_url }));
      setGithubMessage("GitHub 주소를 저장했습니다.");
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "GitHub 주소를 저장하지 못했습니다.");
    } finally {
      setIsSavingGithub(false);
    }
  };

  const roadmap = activeRoadmap;
  const progressPercent = progress?.progress_percent ?? roadmap?.progress_percent ?? 0;
  const completedCount = progress?.completed_count ?? 0;
  const totalCount = progress?.total_count ?? roadmap?.weeks?.flatMap((week) => week.tasks ?? []).length ?? 0;

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
          내 정보
        </Text>
        {isLoading ? (
          <ActivityIndicator color={colors.green} />
        ) : (
          <>
            <InfoRow label="닉네임" value={user?.nickname || "이름 없음"} />
            <InfoRow label="이메일" value={user?.email || "-"} />
            <View style={styles.githubBox}>
              <Text style={styles.infoLabel}>GitHub 주소</Text>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                onChangeText={setGithubUrl}
                placeholder="https://github.com/username"
                placeholderTextColor="#8D948D"
                style={commonStyles.input}
                value={githubUrl}
              />
              <View style={styles.githubActions}>
                <Pressable
                  disabled={isSavingGithub}
                  onPress={saveGithubUrl}
                  style={styles.saveGithubButton}
                >
                  <Text style={styles.saveGithubText}>
                    {isSavingGithub ? "저장 중..." : "저장"}
                  </Text>
                </Pressable>
                {!!user?.github_url && (
                  <Pressable onPress={() => Linking.openURL(user.github_url)}>
                    <Text style={styles.openGithubText}>열기</Text>
                  </Pressable>
                )}
              </View>
              {!!githubMessage && <Text style={styles.savedText}>{githubMessage}</Text>}
            </View>
          </>
        )}
        {!!error && (
          <View style={commonStyles.errorBox}>
            <Text style={commonStyles.errorTitle}>오류가 발생했습니다</Text>
            <Text style={commonStyles.errorText}>{error}</Text>
          </View>
        )}
      </View>

      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          내 로드맵
        </Text>
        {roadmap?.id ? (
          <>
            <InfoRow label="목표 직무" value={roadmap.job_target} />
            <View style={styles.progressBox}>
              <Text style={styles.progressLabel}>진행률</Text>
              <Text style={styles.progressValue}>{progressPercent}%</Text>
              <Text style={commonStyles.bodyText}>
                완료한 할 일 {completedCount}개 / 전체 {totalCount}개
              </Text>
            </View>
          </>
        ) : (
          <Text style={commonStyles.bodyText}>
            아직 저장된 로드맵이 없습니다. 분석을 실행하면 이 계정에 로드맵이 저장됩니다.
          </Text>
        )}
      </View>

      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          계정별 이용 상태
        </Text>
        <Text style={commonStyles.bodyText}>
          지금부터 분석 결과와 로드맵은 로그인한 계정 기준으로 저장되고 불러와집니다.
        </Text>
        <View style={commonStyles.chipWrap}>
          <Text style={commonStyles.chip}>계정 연동 완료</Text>
          <Text style={commonStyles.chip}>로드맵 저장</Text>
          <Text style={commonStyles.chip}>진행률 동기화</Text>
        </View>
      </View>

      <Pressable
        style={[commonStyles.secondaryButton, isSmallScreen && commonStyles.compactButton]}
        onPress={signOut}
      >
        <Text style={commonStyles.secondaryButtonText}>로그아웃</Text>
      </Pressable>
    </ScrollView>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text selectable style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = {
  infoRow: {
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 14,
    borderWidth: 1,
    gap: 5,
    padding: 12,
  },
  infoLabel: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  infoValue: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "800",
    lineHeight: 21,
  },
  githubBox: {
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 14,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  githubActions: {
    alignItems: "center",
    flexDirection: "row",
    gap: 16,
  },
  saveGithubButton: {
    alignItems: "center",
    backgroundColor: colors.green,
    borderRadius: 8,
    justifyContent: "center",
    minHeight: 42,
    minWidth: 94,
    paddingHorizontal: 14,
  },
  saveGithubText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "900",
  },
  openGithubText: {
    color: colors.green,
    fontSize: 14,
    fontWeight: "900",
    textDecorationLine: "underline",
  },
  savedText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "800",
  },
  progressBox: {
    backgroundColor: colors.greenSoft,
    borderRadius: 18,
    gap: 6,
    padding: 14,
  },
  progressLabel: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  progressValue: {
    color: colors.green,
    fontSize: 34,
    fontWeight: "900",
  },
};
