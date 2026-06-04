import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, TextInput, View } from "react-native";

import {
  getMe,
  getMyRoadmap,
  requestProjectAiReview,
  submitProjectForEvaluation,
} from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function AssignmentReviewScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const { activeRoadmap, setActiveRoadmap } = useAnalysis();
  const [expandedProject, setExpandedProject] = useState(null);
  const [forms, setForms] = useState({});
  const [formErrors, setFormErrors] = useState({});
  const [pendingProject, setPendingProject] = useState(null);
  const [pendingAiReview, setPendingAiReview] = useState(null);
  const [isLoading, setIsLoading] = useState(!activeRoadmap);
  const [error, setError] = useState("");
  const [savedGithubUrl, setSavedGithubUrl] = useState("");

  useEffect(() => {
    let mounted = true;
    Promise.all([getMyRoadmap(), getMe()])
      .then(([data, me]) => {
        if (!mounted) return;
        if (data?.roadmap) setActiveRoadmap(data.roadmap);
        setSavedGithubUrl(me?.github_url ?? "");
      })
      .catch((requestError) => {
        if (mounted) {
          setError(requestError.response?.data?.detail ?? "과제 정보를 불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [setActiveRoadmap]);

  const toggleForm = (cycleIndex, submission) => {
    const defaultGithubUrl = submission?.github_url ?? savedGithubUrl;
    setExpandedProject((current) => (current === cycleIndex ? null : cycleIndex));
    setForms((current) => ({
      ...current,
      [cycleIndex]: current[cycleIndex] ?? createEmptyForm(defaultGithubUrl),
    }));
    setError("");
  };

  const updateForm = (cycleIndex, field, value) => {
    setForms((current) => ({
      ...current,
      [cycleIndex]: { ...(current[cycleIndex] ?? createEmptyForm()), [field]: value },
    }));
    setFormErrors((current) => ({
      ...current,
      [cycleIndex]: { ...(current[cycleIndex] ?? {}), [field]: null },
    }));
  };

  const submitProject = async (cycleIndex) => {
    const form = forms[cycleIndex] ?? createEmptyForm();
    const validationErrors = validateForm(form);
    if (Object.keys(validationErrors).length) {
      setFormErrors((current) => ({ ...current, [cycleIndex]: validationErrors }));
      setError("평가를 실행하려면 표시된 필수 내용을 먼저 입력해주세요.");
      return;
    }
    setPendingProject(cycleIndex);
    setError("");
    try {
      const result = await submitProjectForEvaluation({
        cycle_index: cycleIndex,
        github_url: form.githubUrl.trim() || null,
        problem_statement: form.problemStatement.trim(),
        data_description: buildDataDescription(form),
        skills_used: splitValues(form.skillsUsed),
        methods_used: splitValues(form.methodsUsed),
        metrics_used: uniqueItems([...splitValues(form.evidenceMethods), ...inferMetricItems(form.resultSummary)]),
        result_summary: buildResultSummary(form),
        improvement_notes: form.improvementNotes.trim(),
        readme_text: null,
        execution_url: null,
      });
      setActiveRoadmap(result.roadmap);
      setFormErrors((current) => ({ ...current, [cycleIndex]: {} }));
    } catch (requestError) {
      setError(formatRequestError(requestError, "과제 평가를 실행하지 못했습니다."));
    } finally {
      setPendingProject(null);
    }
  };

  const runAiReview = async (submissionId) => {
    Alert.alert(
      "AI 리뷰 실행",
      "OpenAI API를 1회 호출합니다. 점수는 바뀌지 않고, 제출한 증빙 텍스트를 기준으로 엄격한 보완 피드백만 생성합니다.",
      [
        { text: "취소", style: "cancel" },
        {
          text: "실행",
          style: "destructive",
          onPress: async () => {
            setPendingAiReview(submissionId);
            setError("");
            try {
              const result = await requestProjectAiReview(submissionId);
              setActiveRoadmap(result.roadmap);
            } catch (requestError) {
              setError(requestError.response?.data?.detail ?? "AI 리뷰를 실행하지 못했습니다.");
            } finally {
              setPendingAiReview(null);
            }
          },
        },
      ],
    );
  };

  const blueprints = activeRoadmap?.project_blueprints ?? [];
  const submissions = activeRoadmap?.project_submissions ?? [];
  const evidenceScore = activeRoadmap?.project_evidence_score ?? 0;

  if (isLoading && !activeRoadmap) {
    return (
      <View style={[commonStyles.safeArea, styles.center]}>
        <ActivityIndicator color={colors.green} size="large" />
      </View>
    );
  }

  if (!activeRoadmap?.id) {
    return (
      <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
        <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
          <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
            과제검증
          </Text>
          <Text style={commonStyles.bodyText}>
            먼저 분석을 실행하면 직무에 맞는 프로젝트 과제와 앱이 제공하는 검증 기준이 생성됩니다.
          </Text>
          <Pressable style={commonStyles.primaryButton} onPress={() => navigation.navigate("Input")}>
            <Text style={commonStyles.primaryButtonText}>새로 분석하기</Text>
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={screenPadding(contentBottomPadding, isSmallScreen)}>
      <View style={[commonStyles.card, styles.headerCard]}>
        <Text style={styles.headerLabel}>프로젝트 결과물 검증</Text>
        <Text style={styles.headerTitle}>{activeRoadmap.job_target}</Text>
        <Text style={styles.headerScore}>{evidenceScore} / 25점</Text>
        <Text style={styles.headerCopy}>
          프로젝트 증명도는 앱이 제공한 기준으로 결과물의 증빙 충실도를 평가해 지원 준비 점수에 반영합니다.
        </Text>
      </View>

      {blueprints.map((blueprint, index) => {
        const cycleIndex = index + 1;
        const submission = submissions.find((item) => item.cycle_index === cycleIndex);
        return (
          <AssignmentCard
            blueprint={blueprint}
            form={forms[cycleIndex] ?? createEmptyForm(submission?.github_url ?? savedGithubUrl)}
            formErrors={formErrors[cycleIndex] ?? {}}
            index={index}
            isExpanded={expandedProject === cycleIndex}
            isPending={pendingProject === cycleIndex}
            isReviewPending={pendingAiReview === submission?.id}
            key={blueprint.title}
            onAiReview={runAiReview}
            onChange={updateForm}
            onSubmit={submitProject}
            onToggle={() => toggleForm(cycleIndex, submission)}
            submission={submission}
          />
        );
      })}

      {!!error && (
        <View style={commonStyles.errorBox}>
          <Text style={commonStyles.errorTitle}>처리하지 못했습니다</Text>
          <Text style={commonStyles.errorText}>{error}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function AssignmentCard({
  blueprint,
  form,
  formErrors,
  index,
  isExpanded,
  isPending,
  isReviewPending,
  onAiReview,
  onChange,
  onSubmit,
  onToggle,
  submission,
}) {
  const cycleIndex = index + 1;
  return (
    <View style={commonStyles.card}>
      <View style={styles.assignmentHeader}>
        <View style={styles.assignmentTitleBlock}>
          <Text style={styles.cycleLabel}>{cycleIndex}사이클 과제</Text>
          <Text style={styles.assignmentTitle}>{blueprint.title}</Text>
        </View>
        <Text style={[styles.statusBadge, statusStyle(submission?.evaluation?.status)]}>
          {statusLabel(submission?.evaluation?.status)}
        </Text>
      </View>
      <Text style={commonStyles.bodyText}>{blueprint.problem}</Text>
      <CompactSection title="핵심 구현" items={blueprint.techniques} />
      <CompactSection title="앱 제공 검증 기준" items={blueprint.evaluation} />

      <Pressable style={styles.formToggle} onPress={onToggle}>
        <Text style={styles.formToggleText}>
          {isExpanded ? "제출 입력 닫기" : submission ? "수정 제출하기" : "결과물 제출하기"}
        </Text>
      </Pressable>

      {isExpanded && (
        <SubmissionForm
          cycleIndex={cycleIndex}
          form={form}
          formErrors={formErrors}
          isPending={isPending}
          onChange={onChange}
          onSubmit={onSubmit}
        />
      )}
      {!!submission?.evaluation && (
        <EvaluationPanel
          evaluation={submission.evaluation}
          isReviewPending={isReviewPending}
          onAiReview={() => onAiReview(submission.id)}
        />
      )}
    </View>
  );
}

function SubmissionForm({ cycleIndex, form, formErrors, isPending, onChange, onSubmit }) {
  return (
    <View style={styles.form}>
      <Text style={styles.notice}>
        GitHub 링크에서 README만 자동으로 가져와 증빙으로 사용합니다. 저장소 코드를 실행하거나 코드리뷰를 하지는 않습니다.
      </Text>
      {!!form.githubUrl && (
        <Text style={styles.savedGithubNotice}>
          저장된 GitHub 주소가 입력되어 있습니다. 과제 저장소 주소가 다르면 수정해주세요.
        </Text>
      )}
      <SubmissionInput label="GitHub URL (README 자동 수집)" value={form.githubUrl} onChangeText={(value) => onChange(cycleIndex, "githubUrl", value)} />
      <SubmissionInput error={formErrors.problemStatement} multiline label="이 프로젝트가 해결한 문제 *" value={form.problemStatement} onChangeText={(value) => onChange(cycleIndex, "problemStatement", value)} />
      <SubmissionInput label="보여주고 싶은 직무 스킬 (쉼표 구분)" value={form.skillsUsed} onChangeText={(value) => onChange(cycleIndex, "skillsUsed", value)} />
      <SubmissionInput label="사용한 모델 또는 구현 방식 (쉼표 구분)" value={form.methodsUsed} onChangeText={(value) => onChange(cycleIndex, "methodsUsed", value)} />
      <SubmissionInput error={formErrors.techReason} multiline label="왜 이 기술/모델을 사용했나요? *" value={form.techReason} onChangeText={(value) => onChange(cycleIndex, "techReason", value)} />
      <SubmissionInput label="결과 증빙 방식 (쉼표 구분)" value={form.evidenceMethods} onChangeText={(value) => onChange(cycleIndex, "evidenceMethods", value)} />
      <SubmissionInput error={formErrors.resultSummary} multiline label="측정 결과와 비교 내용 *" value={form.resultSummary} onChangeText={(value) => onChange(cycleIndex, "resultSummary", value)} />
      <SubmissionInput error={formErrors.improvementNotes} multiline label="실패 사례, 한계, 개선 계획 *" value={form.improvementNotes} onChangeText={(value) => onChange(cycleIndex, "improvementNotes", value)} />
      <Pressable disabled={isPending} style={styles.evaluateButton} onPress={() => onSubmit(cycleIndex)}>
        <Text style={styles.evaluateButtonText}>{isPending ? "평가 중..." : "무료 규칙 평가 실행"}</Text>
      </Pressable>
    </View>
  );
}

function SubmissionInput({ error, label, multiline = false, onChangeText, value }) {
  return (
    <View style={commonStyles.field}>
      <Text style={commonStyles.label}>{label}</Text>
      <TextInput
        multiline={multiline}
        onChangeText={onChangeText}
        style={[commonStyles.input, multiline && commonStyles.textArea, !!error && styles.invalidInput]}
        value={value}
      />
      {!!error && <Text style={styles.fieldError}>{error}</Text>}
    </View>
  );
}

function EvaluationPanel({ evaluation, isReviewPending, onAiReview }) {
  const aiReview = evaluation.ai_review;
  return (
    <View style={styles.evaluation}>
      <View style={styles.scoreRow}>
        <Text style={styles.sectionTitle}>무료 평가 결과</Text>
        <Text style={styles.ruleScore}>{evaluation.rule_score} / 100</Text>
      </View>
      <Text style={styles.evidencePoints}>
        지원 준비 점수에 프로젝트 증명도 +{evaluation.project_evidence_points}점 반영
      </Text>
      <CompactScoreBreakdown breakdown={evaluation.score_breakdown} />
      {(evaluation.passed_checks ?? []).slice(0, 5).map((item) => (
        <Text key={item} style={styles.passedText}>확인: {item}</Text>
      ))}
      {(evaluation.critical_issues ?? []).map((issue) => (
        <Text key={issue} style={styles.issueText}>- {issue}</Text>
      ))}
      {(evaluation.missing_checks ?? []).slice(0, 4).map((item) => (
        <Text key={item} style={styles.requiredText}>보완: {item}</Text>
      ))}
      {!aiReview && (
        <>
          <Text style={styles.aiNotice}>
            AI 리뷰는 요청할 때만 OpenAI API를 1회 호출합니다. 점수는 올리지 않고, 제출한 증빙 텍스트에서 확인되지 않는 주장과 수정 우선순위만 검토합니다.
          </Text>
          <Pressable disabled={isReviewPending} style={styles.aiButton} onPress={onAiReview}>
            <Text style={styles.aiButtonText}>
              {isReviewPending ? "AI 검토 중..." : "AI에게 엄격 평가받기"}
            </Text>
          </Pressable>
        </>
      )}
      {!!aiReview && (
        <View style={styles.aiResult}>
          <Text style={styles.aiTitle}>AI 평가 결과: {verdictLabel(aiReview.verdict)}</Text>
          <Text style={commonStyles.bodyText}>{aiReview.summary}</Text>
          <CompactSection title="검증되지 않은 주장" items={aiReview.unverified_claims} />
          <CompactSection title="필수 수정 항목" items={aiReview.critical_issues} />
          <CompactSection title="다음 수정 순서" items={aiReview.next_actions} />
        </View>
      )}
    </View>
  );
}

function CompactScoreBreakdown({ breakdown }) {
  const entries = Object.entries(breakdown ?? {});
  if (!entries.length) return null;
  return (
    <View style={styles.breakdownBox}>
      {entries.map(([label, score]) => (
        <View key={label} style={styles.breakdownRow}>
          <Text style={styles.breakdownLabel}>{label}</Text>
          <Text style={styles.breakdownValue}>{score}점</Text>
        </View>
      ))}
    </View>
  );
}

function CompactSection({ title, items }) {
  if (!(items ?? []).length) return null;
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {items.map((item) => <Text key={`${title}-${item}`} style={styles.item}>- {item}</Text>)}
    </View>
  );
}

function createEmptyForm(githubUrl = "") {
  return {
    githubUrl,
    problemStatement: "",
    skillsUsed: "",
    methodsUsed: "",
    techReason: "",
    evidenceMethods: "",
    resultSummary: "",
    improvementNotes: "",
  };
}

function validateForm(form) {
  const errors = {};
  if (form.problemStatement.trim().length < 10) {
    errors.problemStatement = "문제 정의를 10자 이상 입력해주세요.";
  }
  if (form.resultSummary.trim().length < 5) {
    errors.resultSummary = "측정한 결과를 5자 이상 입력해주세요.";
  }
  if (form.techReason.trim().length < 10) {
    errors.techReason = "기술/모델을 선택한 이유를 10자 이상 입력해주세요.";
  }
  if (form.improvementNotes.trim().length < 5) {
    errors.improvementNotes = "한계 또는 개선 계획을 5자 이상 입력해주세요.";
  }
  return errors;
}

function formatRequestError(requestError, fallback) {
  const detail = requestError.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(" / ") || fallback;
  }
  return fallback;
}

function splitValues(value) {
  return String(value ?? "").split(",").map((item) => item.trim()).filter(Boolean);
}

function buildDataDescription(form) {
  const skills = splitValues(form.skillsUsed);
  const methods = splitValues(form.methodsUsed);
  const reason = form.techReason.trim();
  const parts = [
    "GitHub README 자동 수집 결과와 사용자가 입력한 핵심 설명을 기준으로 평가합니다.",
    skills.length ? `사용 기술: ${skills.join(", ")}` : "",
    methods.length ? `구현 방식: ${methods.join(", ")}` : "",
    reason ? `기술/모델 선택 이유: ${reason}` : "",
  ].filter(Boolean);
  return parts.join(" ");
}

function buildResultSummary(form) {
  const evidence = splitValues(form.evidenceMethods);
  const prefix = evidence.length ? `결과 증빙 방식: ${evidence.join(", ")}. ` : "";
  return `${prefix}${form.resultSummary.trim()}`;
}

function inferMetricItems(resultSummary) {
  const text = String(resultSummary ?? "");
  const metrics = [];
  const metricPatterns = [
    ["정확도", /정확도|accuracy/i],
    ["F1", /\bF1\b|f1-score/i],
    ["RMSE", /\bRMSE\b/i],
    ["MAE", /\bMAE\b/i],
    ["응답 시간", /응답\s*시간|latency|ms\b/i],
    ["문서 수", /문서|공고|후보|건/i],
    ["비용", /비용|cost|달러|\\$/i],
    ["누락 건수", /누락|missing|0건/i],
    ["비교 결과", /비교|baseline|베이스라인/i],
  ];
  for (const [label, pattern] of metricPatterns) {
    if (pattern.test(text)) metrics.push(label);
  }
  if (!metrics.length && /\d/.test(text)) metrics.push("수치 측정 결과");
  return metrics.slice(0, 8);
}

function uniqueItems(items) {
  return [...new Set(items.map((item) => String(item ?? "").trim()).filter(Boolean))].slice(0, 20);
}

function statusLabel(status) {
  if (status === "evidence_ready") return "평가 준비 완료";
  if (status === "needs_revision") return "수정 필요";
  if (status === "insufficient_evidence") return "근거 부족";
  return "미제출";
}

function statusStyle(status) {
  return status === "evidence_ready" ? styles.readyStatus : styles.pendingStatus;
}

function verdictLabel(verdict) {
  if (verdict === "acceptable") return "검토 가능";
  if (verdict === "needs_revision") return "수정 필요";
  return "근거 부족";
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
  center: {
    alignItems: "center",
    justifyContent: "center",
  },
  headerCard: {
    backgroundColor: "#1F6F68",
  },
  headerLabel: {
    color: "#C9F0DF",
    fontSize: 13,
    fontWeight: "900",
  },
  headerTitle: {
    color: "#FFFFFF",
    fontSize: 23,
    fontWeight: "900",
  },
  headerScore: {
    color: "#FFFFFF",
    fontSize: 32,
    fontWeight: "900",
  },
  headerCopy: {
    color: "#D9EEE5",
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 20,
  },
  assignmentHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: 8,
    justifyContent: "space-between",
  },
  assignmentTitleBlock: {
    flex: 1,
    gap: 5,
  },
  cycleLabel: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  assignmentTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
    lineHeight: 23,
  },
  statusBadge: {
    borderRadius: 6,
    fontSize: 11,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  readyStatus: {
    backgroundColor: colors.greenSoft,
    color: colors.green,
  },
  pendingStatus: {
    backgroundColor: "#17212B",
    color: "#FFFFFF",
  },
  section: {
    gap: 4,
  },
  sectionTitle: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  item: {
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
  },
  formToggle: {
    alignItems: "center",
    backgroundColor: colors.greenSoft,
    borderColor: "#C9DED4",
    borderRadius: 8,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 48,
  },
  formToggleText: {
    color: colors.green,
    fontSize: 14,
    fontWeight: "900",
  },
  form: {
    borderTopColor: "#E3DACD",
    borderTopWidth: 1,
    gap: 11,
    paddingTop: 12,
  },
  notice: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 20,
  },
  savedGithubNotice: {
    backgroundColor: colors.greenSoft,
    borderRadius: 8,
    color: colors.green,
    fontSize: 12,
    fontWeight: "800",
    lineHeight: 18,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  invalidInput: {
    borderColor: colors.danger,
  },
  fieldError: {
    color: colors.danger,
    fontSize: 12,
    fontWeight: "800",
  },
  evaluateButton: {
    alignItems: "center",
    backgroundColor: colors.green,
    borderRadius: 8,
    justifyContent: "center",
    minHeight: 48,
  },
  evaluateButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "900",
  },
  evaluation: {
    backgroundColor: "#F4F8F5",
    borderColor: "#C9DED4",
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  scoreRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  ruleScore: {
    color: colors.green,
    fontSize: 16,
    fontWeight: "900",
  },
  evidencePoints: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
  breakdownBox: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D6E4DD",
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
    padding: 10,
  },
  breakdownRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  breakdownLabel: {
    color: colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: "800",
  },
  breakdownValue: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  passedText: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "800",
    lineHeight: 18,
  },
  issueText: {
    color: colors.danger,
    fontSize: 13,
    fontWeight: "800",
    lineHeight: 20,
  },
  requiredText: {
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
  },
  aiNotice: {
    borderTopColor: "#D6E4DD",
    borderTopWidth: 1,
    color: colors.muted,
    fontSize: 12,
    lineHeight: 18,
    paddingTop: 8,
  },
  aiButton: {
    alignItems: "center",
    backgroundColor: "#17212B",
    borderRadius: 8,
    justifyContent: "center",
    minHeight: 46,
  },
  aiButtonText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "900",
  },
  aiResult: {
    borderTopColor: "#D6E4DD",
    borderTopWidth: 1,
    gap: 8,
    paddingTop: 10,
  },
  aiTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
};
