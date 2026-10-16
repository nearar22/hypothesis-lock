import { createAccount, createClient } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

const contract = process.env.CONTRACT_ADDRESS?.trim();
const raw = process.env.GENLAYER_PRIVATE_KEY?.trim();
if (!contract || !raw) throw new Error("CONTRACT_ADDRESS and GENLAYER_PRIVATE_KEY are required");
const key = raw.startsWith("0x") ? raw : `0x${raw}`;
const chain = { ...studioDevnet, id: 61997, name: "GenLayer Studio Next", rpcUrls: { default: { http: ["https://studio-next.genlayer.com/api"] } } };
const client = createClient({ chain, account: createAccount(key) });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const id = process.env.STUDY_ID?.trim() || `hypothesis-lock-${Date.now().toString(36)}`;
const prereg = process.env.PREREGISTRATION_URL?.trim() || "https://raw.githubusercontent.com/nearar22/hypothesis-lock/main/docs/preregistration.txt";
const report = process.env.FINAL_REPORT_URL?.trim() || "https://cdn.jsdelivr.net/gh/nearar22/hypothesis-lock@main/docs/final-report.txt";

async function finalized(hash) {
  for (let index = 0; index < 300; index++) {
    const receipt = await client.getTransaction({ hash }).catch(() => null);
    const status = String(receipt?.statusName ?? receipt?.status ?? "PENDING").toUpperCase();
    if (status === "FINALIZED") return receipt;
    if (["UNDETERMINED", "DECLINED", "CANCELED", "CANCELLED"].includes(status)) throw new Error(`Transaction ended ${status}`);
    await sleep(3000);
  }
  throw new Error("Transaction timed out");
}

async function write(label, functionName, args, intelligent = false) {
  const fees = await client.estimateTransactionFees({ leaderTimeunitsAllocation: intelligent ? 500n : 180n, validatorTimeunitsAllocation: intelligent ? 600n : 360n });
  const hash = await client.writeContract({ address: contract, functionName, args, fees });
  console.log(`${label}_TX=${hash}`);
  const receipt = await finalized(hash);
  const execution = String(receipt.txExecutionResultName ?? receipt.txExecutionResult);
  if (execution !== "FINISHED_WITH_RETURN") throw new Error(`${label} failed: ${execution}`);
  return hash;
}

if (!process.env.STUDY_ID?.trim()) {
  await write("CREATE", "create_study", [id, "Application reminder trial", "Does one reminder increase the proportion of first-time applicants who submit a complete application?", prereg]);
  await write("FREEZE_PREREG", "freeze_preregistration", [id], true);
  await write("SUBMIT_REPORT", "submit_report", [id, report, "NONE"]);
  await write("FREEZE_REPORT", "freeze_report", [id], true);
}
await write("EVALUATE", "evaluate_report", [id], true);
const state = await client.readContract({ address: contract, functionName: "get_study", args: [id], jsonSafeReturn: true });
console.log(`STUDY_ID=${id}\nSTATE=${state.status}\nGATE=${state.trust_gate}\nPRIMARY_OUTCOME_STATE=${state.matrix?.dimensions?.[1]?.state}`);
if (state.status !== "SELECTIVE_REPORTING" || state.trust_gate !== "BLOCKED" || state.matrix?.dimensions?.[1]?.state !== "UNDISCLOSED_CHANGE") throw new Error("Live preregistration lifecycle did not reach the expected blocked state");

