import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { createCareerPath, createUserProfile } from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { commonStyles } from "../styles/commonStyles";

const initialForm = {
  job_target: "AI Backend Developer",
  experience_level: "Junior",
  skills: "Python, SQL, FastAPI",
  goal_period: "12",
  target_skill: "RAG",
};

export default function InputScreen({
  contentBottomPadding = 112,
  isSmallScreen = false,
  navigation,
}) {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { setActiveRoadmap, setAnalysisResult, setLastSkills } = useAnalysis();

  const skillList = useMemo(
    () =>
      form.skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
    [form.skills],
  );

  const updateForm = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const runAnalysis = async () => {
    setError("");
    setIsLoading(true);

    try {
      const profilePayload = {
        job_target: form.job_target,
        experience_level: form.experience_level,
        skills: skillList,
        goal_period: Number(form.goal_period) || 12,
      };

      console.log("[API] POST /api/v1/users/profile", profilePayload);
      const profile = await createUserProfile(profilePayload);
      console.log("[API] /api/v1/users/profile response", profile);

      const careerPathPayload = {
        job_role: form.job_target,
        target_skill: form.target_skill,
      };

      console.log("[API] POST /api/v1/agent/career-path");
      console.log("[API] /api/v1/agent/career-path payload", careerPathPayload);
      const careerPath = await createCareerPath(careerPathPayload);
      console.log("[API] /api/v1/agent/career-path response", careerPath);

      const currentSkills = skillList;
      const recommendedSkills =
        careerPath.recommended_skills ??
        careerPath.recommended_learning ??
        [];
      const missingSkills =
        careerPath.missing_skills ?? recommendedSkills.filter((skill) => !currentSkills.includes(skill));
      const recommendedLearning =
        careerPath.recommended_learning ??
        careerPath.roadmap?.flatMap((step) => step.items ?? []) ??
        recommendedSkills;
      const activeRoadmapFromCareerPath = careerPath.roadmap_12_weeks?.length
        ? {
            id: careerPath.roadmap_id,
            job_target: careerPath.target_role ?? careerPath.future_job ?? form.job_target,
            progress_percent: careerPath.progress_percent ?? 0,
            weeks: careerPath.roadmap_12_weeks,
          }
        : null;

      setLastSkills(skillList);
      setActiveRoadmap(activeRoadmapFromCareerPath);
      setAnalysisResult({
        ...careerPath,
        target_role: careerPath.target_role ?? careerPath.future_job ?? form.job_target,
        fit_score:
          careerPath.fit_score ??
          Math.round((careerPath.demand_probability ?? 0) * 100),
        current_skills: careerPath.current_skills ?? currentSkills,
        missing_skills: missingSkills,
        recommended_learning: recommendedLearning,
        recommended_projects:
          careerPath.recommended_projects ??
          careerPath.roadmap?.map((step) => step.title).filter(Boolean) ??
          [],
        summary:
          careerPath.summary ??
          `${careerPath.future_job ?? form.job_target} needs ${form.target_skill} focused learning and project preparation.`,
        job_target: careerPath.future_job ?? form.job_target,
        experience_level: form.experience_level,
        goal_period: Number(form.goal_period) || 12,
        target_skill: form.target_skill,
      });
      navigation.navigate("Result");
    } catch (requestError) {
      console.error("[Analysis] request failed", {
        data: requestError.response?.data,
        status: requestError.response?.status,
        message: requestError.message,
      });

      const responseData = requestError.response?.data;
      const detail =
        typeof responseData?.detail === "string"
          ? responseData.detail
          : requestError.code === "ECONNABORTED"
            ? "API 서버 응답 시간이 초과되었습니다. 백엔드 주소와 실행 상태를 확인해주세요."
            : JSON.stringify(responseData ?? requestError.message, null, 2);
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
          새로 분석하기
        </Text>
        <Field
          label="목표 직무"
          value={form.job_target}
          onChangeText={(value) => updateForm("job_target", value)}
          placeholder="AI Backend Developer"
          isSmallScreen={isSmallScreen}
        />
        <Field
          label="관심 기술"
          value={form.target_skill}
          onChangeText={(value) => updateForm("target_skill", value)}
          placeholder="RAG"
          isSmallScreen={isSmallScreen}
        />
        <Field
          label="경험 수준"
          value={form.experience_level}
          onChangeText={(value) => updateForm("experience_level", value)}
          placeholder="Junior"
          isSmallScreen={isSmallScreen}
        />
        <Field
          label="보유 기술"
          value={form.skills}
          onChangeText={(value) => updateForm("skills", value)}
          placeholder="Python, SQL, FastAPI"
          multiline
          isSmallScreen={isSmallScreen}
        />
        <Field
          keyboardType="number-pad"
          label="목표 기간(주)"
          value={form.goal_period}
          onChangeText={(value) => updateForm("goal_period", value)}
          placeholder="12"
          isSmallScreen={isSmallScreen}
        />

        <Pressable
          disabled={isLoading}
          style={[
            commonStyles.primaryButton,
            isSmallScreen && commonStyles.compactButton,
            isLoading && { opacity: 0.65 },
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
      </View>
    </ScrollView>
  );
}

function Field({ isSmallScreen, label, multiline = false, ...props }) {
  return (
    <View style={commonStyles.field}>
      <Text style={commonStyles.label}>{label}</Text>
      <TextInput
        multiline={multiline}
        placeholderTextColor="#8D948D"
        style={[
          commonStyles.input,
          isSmallScreen && commonStyles.compactInput,
          multiline && commonStyles.textArea,
        ]}
        {...props}
      />
    </View>
  );
}
