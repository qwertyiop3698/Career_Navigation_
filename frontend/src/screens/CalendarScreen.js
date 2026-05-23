import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";

import { getMyRoadmap, toggleRoadmapTask } from "../api/client";
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
        <View
          key={week.id ?? `week-${week.week_number}-${index}`}
          style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}
        >
          <View style={{ flexDirection: "row", gap: 12 }}>
            <View style={[styles.weekBadge, { height: isSmallScreen ? 42 : 48, width: isSmallScreen ? 48 : 54 }]}>
              <Text style={styles.weekBadgeText}>{week.week_number}주</Text>
            </View>
            <View style={{ flex: 1, gap: 8 }}>
              <Text style={[styles.weekTitle, { fontSize: isSmallScreen ? 15 : 16 }]}>
                {week.title}
              </Text>
              <Text style={commonStyles.bodyText}>{week.goal}</Text>
              {(week.tasks ?? []).map((task, index) => (
                <Pressable
                  key={task.id ?? `task-${task.task_title}-${index}`}
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
                  <Text
                    style={[
                      styles.taskText,
                      task.is_completed && styles.completedTaskText,
                    ]}
                  >
                    {task.task_title}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>
      ))}
    </ScrollView>
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
};
