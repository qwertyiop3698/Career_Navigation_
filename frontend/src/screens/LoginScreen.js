import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { login } from "../api/client";
import { useAuth } from "../navigation/AuthContext";
import { commonStyles } from "../styles/commonStyles";

export default function LoginScreen({ navigation }) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    setIsLoading(true);

    try {
      const data = await login({ email, password });
      const token = data.access_token || data.token;
      if (!token) {
        throw new Error("로그인 응답에 토큰이 없습니다.");
      }
      await signIn(token);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === "string" ? detail : requestError.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={[commonStyles.screen, { flexGrow: 1, justifyContent: "center" }]}>
      <View style={commonStyles.card}>
        <Text style={{ color: "#17483E", fontSize: 30, fontWeight: "900" }}>취업 나침반</Text>
        <Text style={commonStyles.bodyText}>비전공자를 위한 12주 취업 준비 캘린더</Text>

        <Field
          autoCapitalize="none"
          keyboardType="email-address"
          label="이메일"
          onChangeText={setEmail}
          placeholder="you@example.com"
          value={email}
        />
        <Field
          label="비밀번호"
          onChangeText={setPassword}
          placeholder="비밀번호"
          secureTextEntry
          value={password}
        />

        <Pressable
          disabled={isLoading}
          style={[commonStyles.primaryButton, isLoading && { opacity: 0.65 }]}
          onPress={handleLogin}
        >
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={commonStyles.primaryButtonText}>로그인</Text>
          )}
        </Pressable>

        <Pressable onPress={() => navigation.navigate("Signup")}>
          <Text style={{ color: "#17483E", fontWeight: "900", textAlign: "center" }}>
            계정이 없나요? 회원가입
          </Text>
        </Pressable>

        {!!error && (
          <View style={commonStyles.errorBox}>
            <Text style={commonStyles.errorTitle}>로그인 실패</Text>
            <Text style={commonStyles.errorText}>{error}</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

function Field({ label, ...props }) {
  return (
    <View style={commonStyles.field}>
      <Text style={commonStyles.label}>{label}</Text>
      <TextInput placeholderTextColor="#8D948D" style={commonStyles.input} {...props} />
    </View>
  );
}
