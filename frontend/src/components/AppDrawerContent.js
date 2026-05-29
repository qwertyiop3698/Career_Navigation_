import {
  DrawerContentScrollView,
  DrawerItem,
} from "@react-navigation/drawer";
import {
  BookOpen,
  CalendarDays,
  ClipboardCheck,
  ClipboardList,
  GraduationCap,
  Home,
  LogOut,
  UserRound,
} from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

export default function AppDrawerContent({ navigation, onLogout }) {
  const goTab = (screen) => {
    navigation.navigate("MainTabs", { screen });
  };

  return (
    <DrawerContentScrollView
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.header}>
        <Text style={styles.title}>취업 나침반</Text>
        <Text style={styles.subtitle}>비전공자를 위한 12주 취업 준비 캘린더</Text>
      </View>

      <View style={styles.menu}>
        <DrawerItem
          icon={({ color, size }) => <Home color={color} size={size} />}
          label="홈"
          labelStyle={styles.label}
          onPress={() => goTab("Home")}
        />
        <DrawerItem
          icon={({ color, size }) => <ClipboardList color={color} size={size} />}
          label="분석 입력"
          labelStyle={styles.label}
          onPress={() => navigation.navigate("Input")}
        />
        <DrawerItem
          icon={({ color, size }) => <BookOpen color={color} size={size} />}
          label="분석 결과"
          labelStyle={styles.label}
          onPress={() => goTab("Result")}
        />
        <DrawerItem
          icon={({ color, size }) => <CalendarDays color={color} size={size} />}
          label="12주 캘린더"
          labelStyle={styles.label}
          onPress={() => goTab("Calendar")}
        />
        <DrawerItem
          icon={({ color, size }) => <ClipboardCheck color={color} size={size} />}
          label="과제 검증"
          labelStyle={styles.label}
          onPress={() => goTab("Assignment")}
        />
        <DrawerItem
          icon={({ color, size }) => <GraduationCap color={color} size={size} />}
          label="자격증 일정 BETA"
          labelStyle={styles.label}
          onPress={() => navigation.navigate("Certification")}
        />
        <DrawerItem
          icon={({ color, size }) => <UserRound color={color} size={size} />}
          label="내 정보"
          labelStyle={styles.label}
          onPress={() => goTab("Profile")}
        />
      </View>

      <View style={styles.footer}>
        <DrawerItem
          icon={({ color, size }) => <LogOut color={color} size={size} />}
          label="로그아웃"
          labelStyle={styles.logoutLabel}
          onPress={onLogout}
        />
      </View>
    </DrawerContentScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#F7F1E8",
    flexGrow: 1,
    paddingTop: 12,
  },
  header: {
    backgroundColor: "#FFFDF8",
    borderColor: "#E1D7C6",
    borderRadius: 8,
    borderWidth: 1,
    margin: 14,
    padding: 18,
  },
  title: {
    color: "#17483E",
    fontSize: 24,
    fontWeight: "900",
  },
  subtitle: {
    color: "#6D776F",
    fontSize: 13,
    fontWeight: "800",
    lineHeight: 19,
    marginTop: 6,
  },
  menu: {
    flex: 1,
  },
  label: {
    color: "#26332D",
    fontSize: 15,
    fontWeight: "800",
  },
  footer: {
    borderTopColor: "#E1D7C6",
    borderTopWidth: 1,
    marginTop: 12,
    paddingTop: 8,
  },
  logoutLabel: {
    color: "#A53B2A",
    fontSize: 15,
    fontWeight: "900",
  },
});
