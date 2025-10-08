// decode_canard.mjs
import LZString from "lz-string";

// Collect stdin fully
let data = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => data += chunk);
process.stdin.on("end", () => {
  try {
    // Trim only trailing whitespace/newlines
    const cleaned = data.replace(/^\s+|\s+$/g, "");
    const decompressed = LZString.decompressFromUTF16(cleaned);

    if (!decompressed) {
      console.error("DECODE ERROR: decompressed data is empty or invalid.");
      process.exit(2);
    }

    console.log(decompressed);
  } catch (err) {
    console.error("DECODE ERROR:", err.message);
    process.exit(1);
  }
});

// Ensure it ends properly even if piped
process.stdin.resume();
