import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer } from "@react-navigation/native";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { getMe, setAuthToken } from "../api/client";
import { AUTH_ENABLED } from "../config";
import { useAnalysis } from "../context/AnalysisContext";
import AppNavigator from "./AppNavigator";
import AuthNavigator from "./AuthNavigator";
import { AuthContext } from "./AuthContext";

const TOKEN_KEY = "access_token";

export default function RootNavigator() {
  const { resetAnalysis } = useAnalysis();
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState(null);

  useEffect(() => {
    async function restoreToken() {
      if (!AUTH_ENABLED) {
        setAuthToken(null);
        setToken(null);
        setIsLoading(false);
        return;
      }

      const storedToken = await AsyncStorage.getItem(TOKEN_KEY);
      if (!storedToken) {
        setToken(null);
        setIsLoading(false);
        return;
      }
      try {
        setAuthToken(storedToken);
        await getMe();
        setToken(storedToken);
      } catch {
        await AsyncStorage.removeItem(TOKEN_KEY);
        setAuthToken(null);
        resetAnalysis();
        setToken(null);
      }
      setIsLoading(false);
    }

    restoreToken();
  }, [resetAnalysis]);

  const authContext = useMemo(
    () => ({
      token,
      signIn: async (accessToken) => {
        resetAnalysis();
        await AsyncStorage.setItem(TOKEN_KEY, accessToken);
        setAuthToken(accessToken);
        setToken(accessToken);
      },
      signOut: async () => {
        await AsyncStorage.removeItem(TOKEN_KEY);
        setAuthToken(null);
        resetAnalysis();
        setToken(null);
      },
    }),
    [resetAnalysis, token],
  );

  if (isLoading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color="#17483E" size="large" />
      </View>
    );
  }

  return (
    <AuthContext.Provider value={authContext}>
      <NavigationContainer>
        {!AUTH_ENABLED || token ? <AppNavigator /> : <AuthNavigator />}
      </NavigationContainer>
    </AuthContext.Provider>
  );
}

const styles = StyleSheet.create({
  loading: {
    alignItems: "center",
    backgroundColor: "#F7F1E8",
    flex: 1,
    justifyContent: "center",
  },
});
