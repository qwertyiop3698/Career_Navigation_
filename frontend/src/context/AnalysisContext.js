import { createContext, useCallback, useContext, useMemo, useState } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeRoadmap, setActiveRoadmap] = useState(null);
  const [lastSkills, setLastSkills] = useState(["Python", "SQL", "RAG"]);
  const resetAnalysis = useCallback(() => {
    setAnalysisResult(null);
    setActiveRoadmap(null);
    setLastSkills([]);
  }, []);

  const value = useMemo(
    () => ({
      analysisResult,
      activeRoadmap,
      lastSkills,
      setAnalysisResult,
      setActiveRoadmap,
      setLastSkills,
      resetAnalysis,
    }),
    [analysisResult, activeRoadmap, lastSkills, resetAnalysis],
  );

  return (
    <AnalysisContext.Provider value={value}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used inside AnalysisProvider");
  }
  return context;
}
