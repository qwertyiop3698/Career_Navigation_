const path = require("path");
const { FileStore } = require("metro-cache");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

config.cacheStores = [
  new FileStore({
    root: path.join(__dirname, ".metro-cache"),
  }),
];

module.exports = config;
