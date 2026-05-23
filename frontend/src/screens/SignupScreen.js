import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { signup } from "../api/client";
import { useAuth } from "../navigation/AuthContext";
import { commonStyles } from "../styles/commonStyles";

export default function SignupScreen({ navigation }) {
  const { signIn } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSignup = async () => {
    setError("");
    setIsLoading(true);

    try {
      const data = await signup({ name, email, password });
      const token = data.access_token || data.token;
      if (token) {
        await signIn(token);
        return;
      }
      navigation.navigate("Login");
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
        <Text style={{ color: "#17483E", fontSize: 28, fontWeight: "900" }}>회원가입</Text>
        <Text style={commonStyles.bodyText}>취업 준비 캘린더를 저장하려면 계정을 만들어주세요.</Text>

        <Field label="이름" onChangeText={setName} placeholder="홍길동" value={name} />
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
          onPress={handleSignup}
        >
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={commonStyles.primaryButtonText}>회원가입</Text>
          )}
        </Pressable>

        <Pressable onPress={() => navigation.navigate("Login")}>
          <Text style={{ color: "#17483E", fontWeight: "900", textAlign: "center" }}>
            이미 계정이 있나요? 로그인
          </Text>
        </Pressable>

        {!!error && (
          <View style={commonStyles.errorBox}>
            <Text style={commonStyles.errorTitle}>회원가입 실패</Text>
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
