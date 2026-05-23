import "react-native-gesture-handler";
import React, { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import SplashScreen from "./src/components/SplashScreen";
import { AnalysisProvider } from "./src/context/AnalysisContext";
import RootNavigator from "./src/navigation/RootNavigator";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      {showSplash ? (
        <SplashScreen />
      ) : (
        <AnalysisProvider>
          <RootNavigator />
        </AnalysisProvider>
      )}
    </SafeAreaProvider>
  );
}
