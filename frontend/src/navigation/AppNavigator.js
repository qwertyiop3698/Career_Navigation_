import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { BookOpen, CalendarDays, ClipboardList, Home, UserRound } from "lucide-react-native";
import { Pressable, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import AppHeader from "../components/AppHeader";
import { AUTH_ENABLED } from "../config";
import CalendarScreen from "../screens/CalendarScreen";
import HomeScreen from "../screens/HomeScreen";
import InputScreen from "../screens/InputScreen";
import ProfileScreen from "../screens/ProfileScreen";
import ResultScreen from "../screens/ResultScreen";

const Tab = createBottomTabNavigator();

export default function AppNavigator() {
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
        showMenuButton={false}
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
          tabBarStyle:
            route.name === "Input"
              ? { display: "none" }
              : {
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
          tabBarButton: (props) =>
            route.name === "Input" ? null : (
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
        <Tab.Screen name="Profile" options={{ title: "내정보" }}>
          {(props) => (
            <ProfileScreen
              {...props}
              contentBottomPadding={contentBottomPadding}
              isSmallScreen={isSmallScreen}
            />
          )}
        </Tab.Screen>
        <Tab.Screen name="Input" options={{ title: "새로 분석하기" }}>
          {(props) => (
            <InputScreen
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
  if (name === "Profile") return UserRound;
  return ClipboardList;
}
