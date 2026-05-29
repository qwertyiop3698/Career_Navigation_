import { useEffect, useState } from "react";
import { CalendarDays, ExternalLink } from "lucide-react-native";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";

import {
  getCertificationBetaOptions,
  getMyRoadmap,
  includeCertificationInRoadmap,
} from "../api/client";
import { useAnalysis } from "../context/AnalysisContext";
import { colors, commonStyles } from "../styles/commonStyles";

export default function CertificationScreen({ navigation }) {
  const { activeRoadmap, setActiveRoadmap } = useAnalysis();
  const [options, setOptions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingCode, setPendingCode] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadSchedule() {
      setIsLoading(true);
      setError("");
      try {
        const response = await getMyRoadmap();
        const roadmap = response?.roadmap ?? activeRoadmap;
        if (!mounted) return;
        if (roadmap) setActiveRoadmap(roadmap);
        if (roadmap?.job_target !== "Data Scientist") {
          setOptions([]);
          return;
        }
        const schedules = await getCertificationBetaOptions(roadmap.job_target);
        if (mounted) setOptions(schedules);
      } catch (requestError) {
        if (mounted) {
          setError(requestError.response?.data?.detail ?? "시험 일정을 불러오지 못했습니다.");
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    loadSchedule();
    return () => {
      mounted = false;
    };
  }, [setActiveRoadmap]);

  const includePlan = async (code) => {
    setPendingCode(code);
    setError("");
    try {
      const roadmap = await includeCertificationInRoadmap(code);
      setActiveRoadmap(roadmap);
      setOptions((current) =>
        current.map((option) =>
          option.code === code ? { ...option, is_selected: true } : option,
        ),
      );
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "자격증 준비 계획을 추가하지 못했습니다.");
    } finally {
      setPendingCode(null);
    }
  };

  const targetRole = activeRoadmap?.job_target;

  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>선택형 준비 항목 BETA</Text>
        <Text style={styles.title}>자격증 시험 일정</Text>
        <Text style={styles.description}>
          Data Scientist 로드맵에서 SQLD와 ADsP를 선택해 4주 준비 계획으로 추가할 수
          있습니다. 자격증은 현재 달성률 점수에 반영되지 않습니다.
        </Text>
      </View>

      {isLoading ? (
        <ActivityIndicator color={colors.green} size="large" />
      ) : targetRole !== "Data Scientist" ? (
        <View style={commonStyles.card}>
          <Text style={commonStyles.cardTitle}>현재 지원 직무</Text>
          <Text style={commonStyles.bodyText}>
            자격증 일정 BETA는 현재 Data Scientist 로드맵에만 제공됩니다.
          </Text>
          <Pressable style={commonStyles.lightButton} onPress={() => navigation.navigate("MainTabs", { screen: "Home" })}>
            <Text style={commonStyles.lightButtonText}>홈으로 돌아가기</Text>
          </Pressable>
        </View>
      ) : (
        options.map((option) => (
          <View key={option.code} style={commonStyles.card}>
            <View style={styles.certificateHeading}>
              <View style={styles.iconBox}>
                <CalendarDays color={colors.green} size={21} />
              </View>
              <View style={styles.headingCopy}>
                <Text style={styles.certificateTitle}>{option.name}</Text>
                <Text style={styles.round}>{option.round} / {option.provider}</Text>
              </View>
            </View>
            <Text style={commonStyles.bodyText}>{option.fit_reason}</Text>
            <View style={styles.schedule}>
              <DateRow label="권장 시작" value={formatDate(option.recommended_start_date)} />
              <DateRow label="원서 접수" value={`${formatDate(option.registration_start)} - ${formatDate(option.registration_end)}`} />
              <DateRow label="시험일" value={formatDate(option.exam_date)} />
              <DateRow label="결과 발표" value={formatDate(option.result_date)} />
            </View>
            <Pressable
              disabled={option.is_selected || pendingCode === option.code}
              onPress={() => includePlan(option.code)}
              style={[
                commonStyles.primaryButton,
                option.is_selected && styles.selectedButton,
              ]}
            >
              <Text style={commonStyles.primaryButtonText}>
                {option.is_selected
                  ? "로드맵에 추가됨"
                  : pendingCode === option.code
                    ? "추가 중..."
                    : "4주 준비 계획 추가"}
              </Text>
            </Pressable>
            <Pressable onPress={() => Linking.openURL(option.official_url)} style={styles.link}>
              <Text style={styles.linkText}>공식 시험 일정 확인</Text>
              <ExternalLink color={colors.green} size={14} />
            </Pressable>
          </View>
        ))
      )}

      {!!error && (
        <View style={commonStyles.errorBox}>
          <Text style={commonStyles.errorTitle}>처리하지 못했습니다</Text>
          <Text style={commonStyles.errorText}>{error}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function DateRow({ label, value }) {
  return (
    <View style={styles.dateRow}>
      <Text style={styles.dateLabel}>{label}</Text>
      <Text style={styles.dateValue}>{value}</Text>
    </View>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${year}.${month}.${day}`;
}

const styles = {
  screen: {
    backgroundColor: colors.background,
    gap: 14,
    padding: 20,
    paddingBottom: 32,
  },
  header: {
    gap: 7,
    paddingBottom: 5,
  },
  eyebrow: {
    color: colors.green,
    fontSize: 12,
    fontWeight: "900",
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: "900",
  },
  description: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 21,
  },
  certificateHeading: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  iconBox: {
    alignItems: "center",
    backgroundColor: colors.greenSoft,
    borderRadius: 8,
    height: 42,
    justifyContent: "center",
    width: 42,
  },
  headingCopy: {
    flex: 1,
    gap: 3,
  },
  certificateTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  round: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "700",
  },
  schedule: {
    backgroundColor: "#F4F8F5",
    borderRadius: 8,
    gap: 9,
    padding: 12,
  },
  dateRow: {
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  dateLabel: {
    color: colors.muted,
    fontSize: 13,
    fontWeight: "800",
  },
  dateValue: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
    textAlign: "right",
  },
  selectedButton: {
    backgroundColor: "#617169",
  },
  link: {
    alignItems: "center",
    alignSelf: "center",
    flexDirection: "row",
    gap: 5,
  },
  linkText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "900",
  },
};
