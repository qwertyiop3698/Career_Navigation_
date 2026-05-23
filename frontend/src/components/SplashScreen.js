import { Image, StyleSheet, View } from "react-native";

const logoSource = require("../../assets/images/logo.png");

export default function SplashScreen() {
  return (
    <View style={styles.container}>
      <Image source={logoSource} resizeMode="contain" style={styles.logo} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    backgroundColor: "#F7F1E8",
    flex: 1,
    justifyContent: "center",
  },
  logo: {
    height: 132,
    width: 132,
  },
});
