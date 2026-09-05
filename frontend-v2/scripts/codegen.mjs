// Regenerate src/lib/api-types.ts from the backend's live OpenAPI schema.
// Dumps app.main.app.openapi() with the backend's own venv (no server needs
// to be running) then runs openapi-typescript over the result.
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(here, "..", "..", "backend");
const outDir = path.resolve(here, "..");

const candidates = [
  path.join(backendDir, "venv", "Scripts", "python.exe"),
  path.join(backendDir, "venv", "bin", "python"),
  path.join(backendDir, ".venv", "Scripts", "python.exe"),
  path.join(backendDir, ".venv", "bin", "python"),
];
const python = candidates.find(existsSync);
if (!python) {
  console.error(
    "No backend venv python found. Set up backend/venv (see backend/scripts/setup_venv.sh) first.",
  );
  process.exit(1);
}

const dumpScript =
  "import json; from app.main import app; print(json.dumps(app.openapi()))";
const schemaJson = execFileSync(python, ["-c", dumpScript], {
  cwd: backendDir,
  encoding: "utf-8",
});

const schemaPath = path.join(outDir, "openapi.json");
await import("node:fs/promises").then((fs) => fs.writeFile(schemaPath, schemaJson));
console.log(`wrote ${schemaPath}`);

execFileSync(
  "npx",
  ["openapi-typescript", schemaPath, "-o", path.join(outDir, "src/lib/api-types.ts")],
  { cwd: outDir, stdio: "inherit", shell: true },
);
