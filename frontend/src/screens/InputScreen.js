import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { createCareerPath, createUserProfile, getRoleSkills } from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

const JOB_ROLES = [
  "Backend Developer",
  "Frontend Developer",
  "AI Backend Developer",
  "Data Analyst",
  "Data Engineer",
  "Data Scientist",
  "Builder",
];

const DOMAINS = ["금융", "커머스", "헬스케어", "교육", "콘텐츠", "스포츠", "채용/HR", "직접 입력"];

const CHECKLIST_CANDIDATES = {
  "Backend Developer": ["Java", "Python", "SQL", "Docker", "AWS", "PostgreSQL"],
  "Frontend Developer": ["React", "TypeScript", "JavaScript", "Node.js", "AWS", "Docker"],
  "AI Backend Developer": ["Python", "LLM", "RAG", "Embedding", "Docker", "AWS"],
  "Data Analyst": ["SQL", "Python", "PostgreSQL", "Machine Learning", "AWS"],
  "Data Engineer": ["SQL", "Python", "Airflow", "Spark", "Kafka", "AWS"],
  "Data Scientist": ["Python", "SQL", "Machine Learning", "PyTorch", "Deep Learning", "Spark"],
  Builder: ["Python", "JavaScript", "SQL", "AWS", "Docker", "TypeScript"],
};

const LEVEL_LABELS = [
  "경험 없음",
  "기본 사용",
  "작은 문제 해결",
  "프로젝트 적용",
  "품질까지 적용",
  "배포/설명 가능",
];

const SKILL_ACTIONS = {
  python: [
    "아직 직접 사용한 적이 없습니다.",
    "print, 변수, 조건문을 작성할 수 있습니다.",
    "함수와 반복문으로 작은 문제를 해결할 수 있습니다.",
    "프로젝트 기능에 Python 코드를 적용할 수 있습니다.",
    "예외 처리와 테스트를 포함해 작성할 수 있습니다.",
    "배포된 결과물에서 사용했고 설계 이유를 설명할 수 있습니다.",
  ],
  sql: [
    "아직 직접 사용한 적이 없습니다.",
    "SELECT와 기본 필터를 작성할 수 있습니다.",
    "JOIN과 GROUP BY로 필요한 결과를 만들 수 있습니다.",
    "프로젝트 데이터 조회나 분석에 적용할 수 있습니다.",
    "성능과 데이터 정확성을 확인하며 작성할 수 있습니다.",
    "운영 데이터 구조와 쿼리 선택을 설명할 수 있습니다.",
  ],
};

const initialForm = {
  job_target: "AI Backend Developer",
  interest_domain: "커머스",
  custom_domain: "",
};

export default function InputScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const [form, setForm] = useState(initialForm);
  const [skillAssessments, setSkillAssessments] = useState([]);
  const [isSkillsLoading, setIsSkillsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const customDomainInputRef = useRef(null);
  const { setActiveRoadmap, setAnalysisResult, setLastSkills } = useAnalysis();

  useEffect(() => {
    let mounted = true;
    setIsSkillsLoading(true);
    getRoleSkills(form.job_target, 40)
      .then((rows) => {
        if (!mounted) return;
        const evidenced = new Set(
          rows
            .filter((row) => ["strong", "moderate"].includes(row.evidence_level))
            .map((row) => row.skill.toLowerCase()),
        );
        const candidates = CHECKLIST_CANDIDATES[form.job_target] ?? [];
        const names = candidates.filter((skill) => evidenced.has(skill.toLowerCase()));
        setSkillAssessments(toAssessments(names.length ? names : candidates));
      })
      .catch(() => {
        if (mounted) {
          setSkillAssessments(toAssessments(CHECKLIST_CANDIDATES[form.job_target] ?? []));
        }
      })
      .finally(() => {
        if (mounted) setIsSkillsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [form.job_target]);

  useEffect(() => {
    if (form.interest_domain !== "직접 입력") return;
    const focusTimer = setTimeout(() => customDomainInputRef.current?.focus(), 0);
    return () => clearTimeout(focusTimer);
  }, [form.interest_domain]);

  const updateForm = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const setSkillLevel = (name, level) => {
    setSkillAssessments((current) =>
      current.map((assessment) =>
        assessment.name === name ? { ...assessment, level } : assessment,
      ),
    );
  };

  const runAnalysis = async () => {
    setError("");
    setIsLoading(true);

    try {
      const interestDomain =
        form.interest_domain === "직접 입력"
          ? form.custom_domain.trim() || "커머스"
          : form.interest_domain;
      const profilePayload = {
        job_target: form.job_target,
        interest_domain: interestDomain,
        experience_level: "Junior",
        skill_assessments: skillAssessments,
        goal_period: 12,
      };
      const profile = await createUserProfile(profilePayload);
      const careerPath = await createCareerPath({
        job_role: form.job_target,
        interest_domain: interestDomain,
        target_skill: skillAssessments[0]?.name ?? "Core skill",
        skill_assessments: skillAssessments,
      });
      const currentSkills = profile.skills ?? [];
      const recommendedSkills = careerPath.recommended_skills ?? [];
      const activeRoadmapFromCareerPath = careerPath.roadmap_12_weeks?.length
        ? {
            id: careerPath.roadmap_id,
            job_target: careerPath.future_job ?? form.job_target,
            interest_domain: careerPath.interest_domain ?? interestDomain,
            progress_percent: careerPath.progress_percent ?? 0,
            readiness_score: careerPath.readiness_score ?? 0,
            capability_score: careerPath.capability_score ?? 0,
            project_evidence_score: careerPath.project_evidence_score ?? 0,
            application_readiness_score: careerPath.application_readiness_score ?? 0,
            cycles: careerPath.cycles ?? [],
            evidence_summary: careerPath.evidence_summary ?? [],
            skill_diagnostics: careerPath.skill_diagnostics ?? [],
            project_blueprints: careerPath.project_blueprints ?? [],
            skill_assessments: careerPath.skill_assessments ?? skillAssessments,
            reassessments: [],
            weeks: careerPath.roadmap_12_weeks,
          }
        : null;

      setLastSkills(currentSkills);
      setActiveRoadmap(activeRoadmapFromCareerPath);
      setAnalysisResult({
        ...careerPath,
        target_role: careerPath.future_job ?? form.job_target,
        current_skills: currentSkills,
        skill_assessments: profile.skill_assessments ?? skillAssessments,
        missing_skills: careerPath.missing_skills ?? recommendedSkills,
        recommended_learning: recommendedSkills,
        job_target: careerPath.future_job ?? form.job_target,
        interest_domain: careerPath.interest_domain ?? interestDomain,
      });
      navigation.navigate("MainTabs", { screen: "Home" });
    } catch (requestError) {
      const responseData = requestError.response?.data;
      const detail =
        typeof responseData?.detail === "string"
          ? responseData.detail
          : "분석 요청을 처리하지 못했습니다. 서버 연결 상태를 확인해 주세요.";
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView
      keyboardShouldPersistTaps="handled"
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
          취업 준비 분석
        </Text>
        <Text style={commonStyles.label}>목표 직무</Text>
        <View style={styles.roleWrap}>
          {JOB_ROLES.map((role) => (
            <Pressable
              key={role}
              onPress={() => updateForm("job_target", role)}
              style={[styles.roleButton, form.job_target === role && styles.selectedRole]}
            >
              <Text style={[styles.roleText, form.job_target === role && styles.selectedRoleText]}>
                {role}
              </Text>
            </Pressable>
          ))}
        </View>
        <Text style={commonStyles.label}>관심 소재</Text>
        <Text style={commonStyles.bodyText}>
          프로젝트 기술 추천에는 영향을 주지 않으며, 흥미 있는 데이터 예시와 설명 맥락에만 반영됩니다.
        </Text>
        <View style={styles.roleWrap}>
          {DOMAINS.map((domain) => (
            <Pressable
              key={domain}
              onPress={() => updateForm("interest_domain", domain)}
              style={[styles.roleButton, form.interest_domain === domain && styles.selectedRole]}
            >
              <Text
                style={[styles.roleText, form.interest_domain === domain && styles.selectedRoleText]}
              >
                {domain}
              </Text>
            </Pressable>
          ))}
        </View>
        {form.interest_domain === "직접 입력" && (
          <TextInput
            autoFocus
            onChangeText={(value) => updateForm("custom_domain", value)}
            placeholder="예: 기후테크, 부동산, 게임"
            placeholderTextColor="#8D948D"
            ref={customDomainInputRef}
            returnKeyType="done"
            style={commonStyles.input}
            value={form.custom_domain}
          />
        )}
      </View>

      <View style={[commonStyles.card, isSmallScreen && commonStyles.compactCard]}>
        <Text style={[commonStyles.cardTitle, isSmallScreen && commonStyles.compactTitle]}>
          기술 수행 체크리스트
        </Text>
        <Text style={commonStyles.bodyText}>
          현재 직접 수행할 수 있는 수준을 선택해 주세요. 이 점수는 전체 기준선 중 최대 60점만 반영됩니다.
        </Text>
        {isSkillsLoading ? (
          <ActivityIndicator color={colors.green} />
        ) : (
          skillAssessments.map((assessment) => (
            <SkillChecklist
              assessment={assessment}
              key={assessment.name}
              onChange={(level) => setSkillLevel(assessment.name, level)}
            />
          ))
        )}
      </View>

      <Pressable
        disabled={isLoading || isSkillsLoading}
        style={[
          commonStyles.primaryButton,
          isSmallScreen && commonStyles.compactButton,
          (isLoading || isSkillsLoading) && { opacity: 0.65 },
        ]}
        onPress={runAnalysis}
      >
        {isLoading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={commonStyles.primaryButtonText}>분석 실행</Text>
        )}
      </Pressable>

      {!!error && (
        <View style={commonStyles.errorBox}>
          <Text style={commonStyles.errorTitle}>오류가 발생했습니다</Text>
          <Text style={commonStyles.errorText}>{error}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function SkillChecklist({ assessment, onChange }) {
  const actions = SKILL_ACTIONS[assessment.name.toLowerCase()];
  const description =
    actions?.[assessment.level] ??
    `${assessment.name}: ${LEVEL_LABELS[assessment.level]} 수준으로 수행할 수 있습니다.`;

  return (
    <View style={styles.skillBlock}>
      <Text style={styles.skillTitle}>{assessment.name}</Text>
      <Text style={styles.skillDescription}>{description}</Text>
      <View style={styles.levelRow}>
        {LEVEL_LABELS.map((label, level) => (
          <Pressable
            accessibilityLabel={`${assessment.name} ${label}`}
            key={`${assessment.name}-${level}`}
            onPress={() => onChange(level)}
            style={[styles.levelButton, assessment.level === level && styles.selectedLevel]}
          >
            <Text style={[styles.levelNumber, assessment.level === level && styles.selectedLevelText]}>
              {level}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.levelCaption}>{LEVEL_LABELS[assessment.level]}</Text>
    </View>
  );
}

function toAssessments(skills = []) {
  return skills.map((name) => ({ name, level: 0 }));
}

const styles = {
  roleWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  roleButton: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D1C7B6",
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  selectedRole: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  roleText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "800",
  },
  selectedRoleText: {
    color: "#FFFFFF",
  },
  skillBlock: {
    borderColor: "#D8D1C5",
    borderTopWidth: 1,
    gap: 8,
    paddingTop: 12,
  },
  skillTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  skillDescription: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 19,
    minHeight: 38,
  },
  levelRow: {
    flexDirection: "row",
    gap: 7,
  },
  levelButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D1C7B6",
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    height: 38,
    justifyContent: "center",
  },
  selectedLevel: {
    backgroundColor: colors.green,
    borderColor: colors.green,
  },
  levelNumber: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  selectedLevelText: {
    color: "#FFFFFF",
  },
  levelCaption: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "800",
  },
};
