import { Menu, UserRound } from "lucide-react-native";
import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

const logoSource = require("../../assets/images/logo.png");

export default function AppHeader({
  isLoggedIn = false,
  onMenuPress,
  onLoginPress,
  onProfilePress,
  showMenuButton = false,
  showAuthControls = false,
  subtitle = "비전공자를 위한 12주 취업 준비 캘린더",
}) {
  const { height, width } = useWindowDimensions();
  const isSmallScreen = width < 360 || height < 700;
  const canOpenMenu = showMenuButton && typeof onMenuPress === "function";
  const iconButtonSize = isSmallScreen ? 32 : 36;
  const logoSize = isSmallScreen ? 44 : 50;

  return (
    <SafeAreaView edges={["top"]} style={styles.safeArea}>
      <View
        style={[
          styles.header,
          {
            minHeight: isSmallScreen ? 64 : 74,
            paddingBottom: isSmallScreen ? 8 : 10,
            paddingHorizontal: isSmallScreen ? 12 : 16,
            paddingTop: isSmallScreen ? 7 : 10,
          },
        ]}
      >
        {canOpenMenu ? (
          <Pressable
            accessibilityLabel="메뉴 열기"
            hitSlop={8}
            style={({ pressed }) => [
              styles.iconButton,
              {
                borderRadius: iconButtonSize / 2,
                height: iconButtonSize,
                width: iconButtonSize,
              },
              pressed && styles.pressedButton,
            ]}
            onPress={onMenuPress}
          >
            <Menu color="#17483E" size={isSmallScreen ? 19 : 22} strokeWidth={2.7} />
          </Pressable>
        ) : (
          <View
            accessibilityLabel="취업 나침반 로고"
            style={[
              styles.logoFrame,
              {
                borderRadius: logoSize / 2,
                height: logoSize,
                width: logoSize,
              },
            ]}
          >
            <Image source={logoSource} resizeMode="cover" style={styles.logoImage} />
          </View>
        )}

        <View style={styles.titleBlock}>
          <Text
            adjustsFontSizeToFit
            maxFontSizeMultiplier={1.05}
            minimumFontScale={0.78}
            numberOfLines={1}
            style={[
              styles.title,
              {
                fontSize: isSmallScreen ? 18 : 21,
                lineHeight: isSmallScreen ? 23 : 27,
              },
            ]}
          >
            취업 나침반
          </Text>
          <Text
            adjustsFontSizeToFit
            maxFontSizeMultiplier={1.0}
            minimumFontScale={0.72}
            numberOfLines={1}
            style={[
              styles.subtitle,
              {
                fontSize: isSmallScreen ? 10 : 12,
                lineHeight: isSmallScreen ? 13 : 16,
              },
            ]}
          >
            {subtitle}
          </Text>
        </View>

        <View style={[styles.rightSlot, { minWidth: isSmallScreen ? 38 : 48 }]}>
          {showAuthControls && isLoggedIn ? (
            <Pressable
              accessibilityLabel="사용자 프로필"
              hitSlop={8}
              style={({ pressed }) => [
                styles.profileButton,
                {
                  borderRadius: iconButtonSize / 2,
                  height: iconButtonSize,
                  width: iconButtonSize,
                },
                pressed && styles.pressedButton,
              ]}
              onPress={onProfilePress}
            >
              <UserRound color="#FFFFFF" size={isSmallScreen ? 17 : 19} strokeWidth={2.8} />
            </Pressable>
          ) : showAuthControls ? (
            <Pressable
              disabled={!onLoginPress}
              hitSlop={8}
              style={({ pressed }) => [
                styles.loginButton,
                {
                  minHeight: isSmallScreen ? 30 : 34,
                  paddingHorizontal: isSmallScreen ? 10 : 12,
                },
                pressed && styles.pressedButton,
                !onLoginPress && styles.disabledButton,
              ]}
              onPress={onLoginPress}
            >
              <Text style={[styles.loginText, { fontSize: isSmallScreen ? 11 : 12 }]}>
                로그인
              </Text>
            </Pressable>
          ) : null}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F7F1E8",
  },
  header: {
    alignItems: "center",
    backgroundColor: "#F7F1E8",
    borderBottomColor: "#E2D6C4",
    borderBottomWidth: 1,
    flexDirection: "row",
    gap: 10,
  },
  titleBlock: {
    flex: 1,
    gap: 2,
    minWidth: 0,
  },
  title: {
    color: "#17483E",
    fontWeight: "900",
    letterSpacing: 0,
  },
  subtitle: {
    color: "#657269",
    fontWeight: "700",
    letterSpacing: 0,
  },
  logoFrame: {
    alignItems: "center",
    backgroundColor: "#F7F1E8",
    borderColor: "#DCD1BE",
    borderWidth: 1,
    justifyContent: "center",
    overflow: "hidden",
  },
  logoImage: {
    height: "100%",
    width: "100%",
  },
  iconButton: {
    alignItems: "center",
    backgroundColor: "#FFFDF8",
    borderColor: "#DCD1BE",
    borderWidth: 1,
    justifyContent: "center",
  },
  rightSlot: {
    alignItems: "flex-end",
    flexShrink: 0,
    justifyContent: "center",
  },
  loginButton: {
    alignItems: "center",
    backgroundColor: "#17483E",
    borderRadius: 999,
    justifyContent: "center",
  },
  loginText: {
    color: "#FFFFFF",
    fontWeight: "900",
  },
  profileButton: {
    alignItems: "center",
    backgroundColor: "#17483E",
    borderColor: "#D7E8DD",
    borderWidth: 2,
    justifyContent: "center",
  },
  pressedButton: {
    opacity: 0.78,
  },
  disabledButton: {
    opacity: 0.55,
  },
});
