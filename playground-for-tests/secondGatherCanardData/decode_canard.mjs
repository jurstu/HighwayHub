// decode_canard.js
import fs from "fs";
import LZString from "lz-string";

const stdin = process.stdin;
let data = "";

stdin.setEncoding("utf8");
stdin.on("data", chunk => data += chunk);
stdin.on("end", () => {
  try {
    const decompressed = LZString.decompressFromUTF16(data.trim());
    console.log(decompressed);
  } catch (err) {
    console.error("DECODE ERROR:", err);
    process.exit(1);
  }
});
