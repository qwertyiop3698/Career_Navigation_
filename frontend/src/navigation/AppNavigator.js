import { createDrawerNavigator } from "@react-navigation/drawer";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { BookOpen, CalendarDays, ClipboardCheck, Home, UserRound } from "lucide-react-native";
import { Pressable, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import AppDrawerContent from "../components/AppDrawerContent";
import AppHeader from "../components/AppHeader";
import { AUTH_ENABLED } from "../config";
import AssignmentReviewScreen from "../screens/AssignmentReviewScreen";
import CalendarScreen from "../screens/CalendarScreen";
import CertificationScreen from "../screens/CertificationScreen";
import HomeScreen from "../screens/HomeScreen";
import InputScreen from "../screens/InputScreen";
import ProfileScreen from "../screens/ProfileScreen";
import ResultScreen from "../screens/ResultScreen";
import { useAuth } from "./AuthContext";

const Tab = createBottomTabNavigator();
const Drawer = createDrawerNavigator();

export default function AppNavigator() {
  const { signOut } = useAuth();
  return (
    <Drawer.Navigator
      drawerContent={(props) => <AppDrawerContent {...props} onLogout={signOut} />}
      screenOptions={{
        drawerStyle: { backgroundColor: "#F7F1E8", width: 286 },
        headerShown: false,
      }}
    >
      <Drawer.Screen name="MainTabs" component={MainTabs} />
      <Drawer.Screen
        name="Input"
        component={InputScreen}
        options={{
          headerShown: true,
          headerStyle: { backgroundColor: "#F7F1E8" },
          headerTintColor: "#17483E",
          headerTitle: "새로 분석하기",
          headerShadowVisible: false,
        }}
      />
      <Drawer.Screen
        name="Certification"
        component={CertificationScreen}
        options={{
          headerShown: true,
          headerStyle: { backgroundColor: "#F7F1E8" },
          headerTintColor: "#17483E",
          headerTitle: "자격증 일정",
          headerShadowVisible: false,
        }}
      />
    </Drawer.Navigator>
  );
}

function MainTabs({ navigation }) {
  const insets = useSafeAreaInsets();
  const { height, width } = useWindowDimensions();
  const isSmallScreen = width < 360 || height < 700;
  const bottomPadding = Math.max(insets.bottom, 8);
  const baseTabHeight = isSmallScreen ? 58 : 64;
  const tabBarHeight = baseTabHeight + bottomPadding;
  const iconSize = isSmallScreen ? 18 : 21;
  const labelSize = isSmallScreen ? 10 : 11;
  const contentBottomPadding = baseTabHeight + insets.bottom + 24;

  return (
    <View style={{ backgroundColor: "#F7F1E8", flex: 1 }}>
      <AppHeader
        isLoggedIn
        showAuthControls={AUTH_ENABLED}
        showMenuButton
        onMenuPress={() => navigation.openDrawer()}
        onProfilePress={() => navigation.navigate("MainTabs", { screen: "Profile" })}
      />
      <Tab.Navigator
        initialRouteName="Home"
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: "#17483E",
          tabBarInactiveTintColor: "#6C766F",
          tabBarLabelStyle: {
            fontSize: labelSize,
            fontWeight: "900",
            marginTop: 1,
          },
          tabBarStyle: {
                  alignSelf: "center",
                  backgroundColor: "#F7F1E8",
                  borderColor: "#DED3C1",
                  borderTopLeftRadius: 18,
                  borderTopRightRadius: 18,
                  borderTopWidth: 1,
                  elevation: 8,
                  height: tabBarHeight,
                  maxWidth: 520,
                  paddingBottom: bottomPadding,
                  paddingHorizontal: isSmallScreen ? 4 : 8,
                  paddingTop: isSmallScreen ? 4 : 6,
                  shadowColor: "#3A3024",
                  shadowOffset: { width: 0, height: -2 },
                  shadowOpacity: 0.06,
                  shadowRadius: 8,
                  width: "100%",
                },
          tabBarItemStyle: {
            borderRadius: 14,
            marginHorizontal: isSmallScreen ? 0 : 2,
          },
          tabBarIcon: ({ color, focused }) => {
            const Icon = getTabIcon(route.name);
            return (
              <Icon
                color={focused ? "#17483E" : color}
                size={iconSize}
                strokeWidth={focused ? 3 : 2.3}
              />
            );
          },
          tabBarButton: (props) => (
            <TabButtonWrapper {...props} active={props.accessibilityState?.selected} />
          ),
        })}
      >
        <Tab.Screen name="Home" options={{ title: "홈" }}>
          {(props) => (
            <HomeScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
        <Tab.Screen name="Result" options={{ title: "결과" }}>
          {(props) => (
            <ResultScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
        <Tab.Screen name="Calendar" options={{ title: "로드맵" }}>
          {(props) => (
            <CalendarScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
        <Tab.Screen name="Assignment" options={{ title: "과제검증" }}>
          {(props) => (
            <AssignmentReviewScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
        <Tab.Screen name="Profile" options={{ title: "내정보" }}>
          {(props) => (
            <ProfileScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
      </Tab.Navigator>
    </View>
  );
}

function TabButtonWrapper({ active, children, onPress, style }) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        style,
        {
          alignItems: "center",
          backgroundColor: active ? "#E5F0EA" : "transparent",
          borderRadius: 14,
          justifyContent: "center",
        },
      ]}
    >
      {children}
    </Pressable>
  );
}

function getTabIcon(name) {
  if (name === "Home") return Home;
  if (name === "Result") return BookOpen;
  if (name === "Calendar") return CalendarDays;
  if (name === "Assignment") return ClipboardCheck;
  if (name === "Profile") return UserRound;
  return Home;
}
