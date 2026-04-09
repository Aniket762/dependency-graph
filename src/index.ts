import { Composio } from "@composio/core";

const composio = new Composio();

// Google dataset
// const tools = await composio.tools.getRawComposioTools({
//   toolkits: ["googlesuper"],
//   limit: 1000,
// });

// Github dataset
const tools = await composio.tools.getRawComposioTools({
  toolkits: ["github"],
  limit: 1000,
});

console.log(tools);

import { writeFile } from "fs/promises";

// Google dataset fout 
// await writeFile(
//   "googlesuper_tools.json",
//   JSON.stringify(tools, null, 2),
//   "utf-8"
// );

// GitHub dataset fout
await writeFile(
  "googlesuper_tools.json",
  JSON.stringify(tools, null, 2),
  "utf-8"
);
console.log("Tools written to googlesuper_tools.json");
