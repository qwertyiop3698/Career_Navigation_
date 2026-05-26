import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";

import {
  getMyRoadmap,
  submitRoadmapReassessment,
  toggleRoadmapTask,
} from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function CalendarScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, setActiveRoadmap } = useAnalysis();
  const [isLoading, setIsLoading] = useState(false);
  const [pendingTaskId, setPendingTaskId] = useState(null);
  const [openCheckpoint, setOpenCheckpoint] = useState(null);
  const [reassessmentDraft, setReassessmentDraft] = useState([]);
  const [isSubmittingReassessment, setIsSubmittingReassessment] = useState(false);
  const [reassessmentError, setReassessmentError] = useState("");

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
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
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [setActiveRoadmap]);

  const handleToggleTask = async (taskId) => {
    setPendingTaskId(taskId);
    try {
      const result = await toggleRoadmapTask(taskId);
      setActiveRoadmap(updateTaskInRoadmap(activeRoadmap, result));
    } catch (error) {
      console.error("[Roadmap] failed to toggle task", {
        data: error.response?.data,
        status: error.response?.status,
        message: error.message,
      });
    } finally {
      setPendingTaskId(null);
    }
  };

  const beginReassessment = (checkpointWeek) => {
    setReassessmentError("");
    setOpenCheckpoint(checkpointWeek);
    setReassessmentDraft(
      (activeRoadmap.skill_assessments ?? []).map((assessment) => ({ ...assessment })),
    );
  };

  const updateReassessmentLevel = (name, level) => {
    setReassessmentDraft((current) =>
      current.map((assessment) =>
        assessment.name === name ? { ...assessment, level } : assessment,
      ),
    );
  };

  const saveReassessment = async () => {
    setIsSubmittingReassessment(true);
    setReassessmentError("");
    try {
      const roadmap = await submitRoadmapReassessment({
        checkpoint_week: openCheckpoint,
        skill_assessments: reassessmentDraft,
      });
      setActiveRoadmap(roadmap);
      setOpenCheckpoint(null);
    } catch (error) {
      setReassessmentError(
        error.response?.data?.detail ?? "재진단을 저장하지 못했습니다.",
      );
    } finally {
      setIsSubmittingReassessment(false);
    }
  };

  if (isLoading && !activeRoadmap) {
    return (
      <View style={[commonStyles.safeArea, { alignItems: "center", justifyContent: "center" }]}>
        <ActivityIndicator color={colors.green} size="large" />
      </View>
    );
  }

  if (!activeRoadmap?.id) {
    return (
      <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
            로드맵
          </Text>
          <Text style={commonStyles.bodyText}>
            아직 12주 로드맵이 없습니다. 분석을 먼저 실행하면 주차별 준비 계획을 볼 수 있습니다.
          </Text>
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

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          12주 취업 준비 로드맵
        </Text>
        <Text style={styles.progressText}>{activeRoadmap.progress_percent ?? 0}% 완료</Text>
        <Text style={commonStyles.bodyText}>
          {activeRoadmap.job_target} 준비를 주차별 할 일로 나눴습니다. 완료한 항목을 체크하면 진행률이 바로 반영됩니다.
        </Text>
      </View>

      {(activeRoadmap.weeks ?? []).map((week, index) => (
        <View key={week.id ?? `week-${week.week_number}-${index}`} style={{ gap: 16 }}>
          <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
            <View style={{ flexDirection: "row", gap: 12 }}>
              <View style={[styles.weekBadge, { height: isSmallScreen ? 42 : 48, width: isSmallScreen ? 48 : 54 }]}>
                <Text style={styles.weekBadgeText}>{week.week_number}주</Text>
              </View>
              <View style={{ flex: 1, gap: 8 }}>
                <Text style={[styles.weekTitle, { fontSize: isSmallScreen ? 15 : 16 }]}>
                  {week.title}
                </Text>
                <Text style={commonStyles.bodyText}>{week.goal}</Text>
                {(week.tasks ?? []).map((task, taskIndex) => (
                  <Pressable
                    key={task.id ?? `task-${task.task_title}-${taskIndex}`}
                    disabled={pendingTaskId === task.id}
                    onPress={() => handleToggleTask(task.id)}
                    style={[
                      styles.taskRow,
                      task.is_completed && styles.completedTaskRow,
                      pendingTaskId === task.id && { opacity: 0.6 },
                    ]}
                  >
                    <View style={[styles.checkBox, task.is_completed && styles.checkedBox]}>
                      <Text style={styles.checkText}>{task.is_completed ? "✓" : ""}</Text>
                    </View>
                    <Text style={[styles.taskText, task.is_completed && styles.completedTaskText]}>
                      {task.task_title}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
          </View>
          {[6, 12].includes(week.week_number) && (
            <ReassessmentPanel
              checkpointWeek={week.week_number}
              draft={reassessmentDraft}
              error={reassessmentError}
              isOpen={openCheckpoint === week.week_number}
              isSaved={(activeRoadmap.reassessments ?? []).some(
                (assessment) => assessment.checkpoint_week === week.week_number,
              )}
              isSubmitting={isSubmittingReassessment}
              onBegin={() => beginReassessment(week.week_number)}
              onCancel={() => setOpenCheckpoint(null)}
              onChange={updateReassessmentLevel}
              onSubmit={saveReassessment}
            />
          )}
        </View>
      ))}
    </ScrollView>
  );
}

const LEVEL_LABELS = ["경험 없음", "기본 사용", "문제 해결", "프로젝트 적용", "품질 적용", "설명 가능"];

function ReassessmentPanel({
  checkpointWeek,
  draft,
  error,
  isOpen,
  isSaved,
  isSubmitting,
  onBegin,
  onCancel,
  onChange,
  onSubmit,
}) {
  return (
    <View style={[commonStyles.card, styles.checkpointCard]}>
      <View style={styles.checkpointHeader}>
        <Text style={styles.checkpointTitle}>{checkpointWeek}주차 재진단</Text>
        <Text style={styles.checkpointBadge}>{isSaved ? "저장됨" : "UPDATE"}</Text>
      </View>
      <Text style={commonStyles.bodyText}>
        {checkpointWeek === 6
          ? "전반부 결과를 기준으로 기술 수준을 다시 선택하면 후반부 학습 우선순위와 계획이 바뀝니다."
          : "12주 뒤 변화량을 저장합니다. 이후 유사한 사용자에게 더 나은 계획을 추천할 데이터가 됩니다."}
      </Text>
      {!isOpen && !isSaved && (
        <Pressable style={commonStyles.lightButton} onPress={onBegin}>
          <Text style={commonStyles.lightButtonText}>재진단 시작</Text>
        </Pressable>
      )}
      {isSaved && !isOpen && (
        <Text style={styles.savedText}>이 시점의 변화 기록이 저장되었습니다.</Text>
      )}
      {isOpen && (
        <>
          {draft.map((assessment) => (
            <View key={assessment.name} style={styles.assessmentRow}>
              <Text style={styles.assessmentName}>{assessment.name}</Text>
              <View style={styles.levelButtons}>
                {LEVEL_LABELS.map((label, level) => (
                  <Pressable
                    accessibilityLabel={`${assessment.name} ${label}`}
                    key={`${assessment.name}-${level}`}
                    onPress={() => onChange(assessment.name, level)}
                    style={[
                      styles.levelButton,
                      assessment.level === level && styles.activeLevelButton,
                    ]}
                  >
                    <Text
                      style={[
                        styles.levelButtonText,
                        assessment.level === level && styles.activeLevelText,
                      ]}
                    >
                      {level}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <Text style={styles.selectedLevelLabel}>{LEVEL_LABELS[assessment.level]}</Text>
            </View>
          ))}
          {!!error && <Text style={commonStyles.errorText}>{error}</Text>}
          <Pressable
            disabled={isSubmitting}
            onPress={onSubmit}
            style={[commonStyles.primaryButton, isSubmitting && { opacity: 0.65 }]}
          >
            <Text style={commonStyles.primaryButtonText}>재진단 저장 및 계획 업데이트</Text>
          </Pressable>
          <Pressable onPress={onCancel} style={commonStyles.lightButton}>
            <Text style={commonStyles.lightButtonText}>취소</Text>
          </Pressable>
        </>
      )}
    </View>
  );
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

function updateTaskInRoadmap(roadmap, result) {
  if (!roadmap) return roadmap;
  return {
    ...roadmap,
    progress_percent: result.progress_percent,
    readiness_score: result.readiness_score,
    capability_score: result.capability_score,
    project_evidence_score: result.project_evidence_score,
    application_readiness_score: result.application_readiness_score,
    weeks: roadmap.weeks.map((week) => ({
      ...week,
      tasks: week.tasks.map((task) =>
        task.id === result.task_id
          ? { ...task, is_completed: result.is_completed }
          : task,
      ),
    })),
  };
}

const styles = {
  progressText: {
    color: colors.green,
    fontSize: 28,
    fontWeight: "900",
  },
  weekBadge: {
    alignItems: "center",
    backgroundColor: colors.greenSoft,
    borderRadius: 16,
    justifyContent: "center",
  },
  weekBadgeText: {
    color: colors.green,
    fontWeight: "900",
  },
  weekTitle: {
    color: colors.text,
    fontWeight: "900",
  },
  taskRow: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: colors.cardBorder,
    borderRadius: 14,
    borderWidth: 1,
    flexDirection: "row",
    gap: 10,
    padding: 10,
  },
  completedTaskRow: {
    backgroundColor: "#EAF4EE",
    borderColor: "#BFD8CB",
  },
  checkBox: {
    alignItems: "center",
    borderColor: colors.green,
    borderRadius: 8,
    borderWidth: 2,
    height: 24,
    justifyContent: "center",
    width: 24,
  },
  checkedBox: {
    backgroundColor: colors.green,
  },
  checkText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "900",
  },
  taskText: {
    color: colors.text,
    flex: 1,
    fontSize: 14,
    fontWeight: "800",
    lineHeight: 20,
  },
  completedTaskText: {
    color: colors.muted,
    textDecorationLine: "line-through",
  },
  checkpointCard: {
    backgroundColor: "#F0F7F3",
    borderColor: "#BFD8CB",
    borderRadius: 8,
  },
  checkpointHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  checkpointTitle: {
    color: colors.green,
    fontSize: 17,
    fontWeight: "900",
  },
  checkpointBadge: {
    backgroundColor: colors.green,
    borderRadius: 6,
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "900",
    paddingHorizontal: 7,
    paddingVertical: 4,
  },
  assessmentRow: {
    borderTopColor: "#CFDFD6",
    borderTopWidth: 1,
    gap: 7,
    paddingTop: 10,
  },
  assessmentName: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  levelButtons: {
    flexDirection: "row",
    gap: 6,
  },
  levelButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#C9DED4",
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    height: 36,
    justifyContent: "center",
  },
  activeLevelButton: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  levelButtonText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  activeLevelText: {
    color: "#FFFFFF",
  },
  selectedLevelLabel: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "800",
  },
  savedText: {
    color: colors.green,
    fontSize: 14,
    fontWeight: "800",
  },
};
