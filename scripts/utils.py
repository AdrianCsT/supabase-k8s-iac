from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional


class CmdError(Exception):
    pass


def run(cmd: List[str], cwd: Optional[str]) -> str:
    """Execute a command, stream both pipes, and return ONLY stdout text.

    Important: Some callers JSON-parse the return; never mix stderr into it.
    """
    import threading
    import queue

    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    q: "queue.Queue[tuple[str,str]]" = queue.Queue()
    stdout_buf: list[str] = []

    def pump(pipe, tag: str) -> None:
        try:
            for line in iter(pipe.readline, ""):
                if not line:
                    continue
                line = line.rstrip()
                q.put((tag, line))
                # Echo to console
                print(line, flush=True)
                if tag == "stdout":
                    stdout_buf.append(line)
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    t_out = threading.Thread(target=pump, args=(proc.stdout, "stdout"), daemon=True)
    t_err = threading.Thread(target=pump, args=(proc.stderr, "stderr"), daemon=True)
    t_out.start()
    t_err.start()
    rc = proc.wait()
    t_out.join()
    t_err.join()

    out_text = "\n".join(stdout_buf).strip()
    if rc != 0:
        raise CmdError(f"Command failed ({rc}): {' '.join(cmd)}\nSTDOUT:\n{out_text}")
    return out_text


def aks_invoke(
    resource_group: str,
    cluster_name: str,
    command: str,
    files: Optional[List[Path]] = None,
) -> str:
    base_cmd = [
        _resolve_az_exe(),
        "aks",
        "command",
        "invoke",
        "-g",
        resource_group,
        "-n",
        cluster_name,
        "--command",
        command,
        "--query",
        "logs",
        "-o",
        "tsv",
    ]
    if files:
        for f in files:
            base_cmd.extend(["--file", str(f)])
    return run(base_cmd, cwd=None)


def download_zip(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "src.zip"
    with urllib.request.urlopen(url) as resp, open(zip_path, "wb") as fh:
        fh.write(resp.read())
    return zip_path


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    # GitHub zipball extracts to unknown top folder; find supabase-kubernetes-main
    for p in dest_dir.iterdir():
        if p.is_dir() and p.name.startswith("supabase-kubernetes-"):
            return p
    raise CmdError("Failed to locate extracted supabase-kubernetes directory")


def helm(args: List[str]) -> str:
    return run(["helm", *args], cwd=None)


def package_chart_from_zip(zip_url: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    z = download_zip(zip_url, tmp)
    root = extract_zip(z, tmp)
    chart_dir = root / "charts" / "supabase"
    if not chart_dir.exists():
        raise CmdError(f"Supabase chart directory not found at {chart_dir}")
    # build dependencies and package
    helm(["dependency", "build", str(chart_dir)])
    helm(["package", str(chart_dir), "-d", str(tmp)])
    # find packaged tgz
    for f in tmp.glob("supabase-*.tgz"):
        return f
    raise CmdError("Packaged chart .tgz not found")


def b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def ensure_eso(resource_group: str, cluster_name: str) -> None:
    cmd = " && ".join(
        [
            "helm repo add external-secrets https://charts.external-secrets.io",
            "helm repo update",
            "helm upgrade --install external-secrets external-secrets/external-secrets --namespace external-secrets --create-namespace --set installCRDs=true --wait --timeout=10m",
        ]
    )
    aks_invoke(resource_group, cluster_name, cmd)


def cdktf(project_dir: Path, args: List[str]) -> str:
    return run(["cdktf", *args], cwd=str(project_dir))


def ensure_namespace(resource_group: str, cluster_name: str, namespace: str) -> None:
    cmd = "bash -lc 'kubectl get ns {ns} >/dev/null 2>&1 || kubectl create ns {ns}'".format(
        ns=shlex.quote(namespace)
    )
    aks_invoke(resource_group, cluster_name, cmd)


def install_ingress_nginx(resource_group: str, cluster_name: str) -> None:
    cmd = (
        "helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx && "
        "helm repo update && "
        "helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace --set controller.replicaCount=2"
    )
    aks_invoke(resource_group, cluster_name, cmd)


def annotate_ingress_internal(resource_group: str, cluster_name: str) -> None:
    wait = "bash -lc 'for i in {1..30}; do kubectl -n ingress-nginx get svc ingress-nginx-controller >/dev/null 2>&1 && exit 0; sleep 2; done; exit 1'"
    try:
        aks_invoke(resource_group, cluster_name, wait)
        aks_invoke(
            resource_group,
            cluster_name,
            "kubectl -n ingress-nginx annotate svc ingress-nginx-controller service.beta.kubernetes.io/azure-load-balancer-internal=true --overwrite",
        )
    except CmdError:
        # Non-fatal
        pass


def apply_files_server_side(
    resource_group: str, cluster_name: str, files: List[Path]
) -> None:
    """Apply local manifest files by referencing mounted path in AKS run-command.

    Avoid stdin piping ('no objects passed to apply') by using /command-files.
    """
    for f in files:
        leaf = f.name
        cmd = f"kubectl apply -f /command-files/{leaf}"
        aks_invoke(resource_group, cluster_name, cmd, files=[f])


def helm_list_all(resource_group: str, cluster_name: str) -> str:
    return aks_invoke(resource_group, cluster_name, "helm list -A -o json")


def kubectl_get(resource_group: str, cluster_name: str, ns: str, what: str) -> str:
    return aks_invoke(
        resource_group, cluster_name, f"kubectl -n {shlex.quote(ns)} get {what} -o json"
    )


def kubectl_get_text(resource_group: str, cluster_name: str, ns: str, what: str) -> str:
    return aks_invoke(
        resource_group, cluster_name, f"kubectl -n {shlex.quote(ns)} get {what}"
    )


def upsert_kv_secret(kv_name: str, name: str, value: str) -> None:
    # if exists -> skip, else set
    try:
        existing = az(
            [
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                kv_name,
                "--name",
                name,
                "--query",
                "id",
                "-o",
                "tsv",
            ]
        ).strip()
    except CmdError:
        existing = ""
    if not existing:
        az(
            [
                "keyvault",
                "secret",
                "set",
                "--vault-name",
                kv_name,
                "--name",
                name,
                "--value",
                value,
            ]
        )


def grant_kubelet_kv_role(resource_group: str, cluster_name: str, kv_name: str) -> None:
    aks_show = json.loads(
        az(["aks", "show", "-g", resource_group, "-n", cluster_name, "-o", "json"])
    )
    kubelet_obj = (
        aks_show.get("identityProfile", {}).get("kubeletidentity", {}).get("objectId")
    )
    if not kubelet_obj:
        return
    sub_id = aks_show["id"].split("/")[2]
    scope = f"/subscriptions/{sub_id}/resourceGroups/{resource_group}/providers/Microsoft.KeyVault/vaults/{kv_name}"
    az(
        [
            "role",
            "assignment",
            "create",
            "--assignee-object-id",
            kubelet_obj,
            "--assignee-principal-type",
            "ServicePrincipal",
            "--role",
            "Key Vault Secrets User",
            "--scope",
            scope,
        ]
    )


def apply_yaml_via_b64(
    resource_group: str, cluster_name: str, yaml_content: str
) -> None:
    cmd = f"echo {b64(yaml_content)} | base64 -d | kubectl apply -f -"
    aks_invoke(resource_group, cluster_name, cmd)


def install_chart_server_side(
    resource_group: str,
    cluster_name: str,
    namespace: str,
    release: str,
    chart_tgz: Path,
    values_file: Path,
) -> str:
    # Use server-side script referencing /command-files
    script = f"""#!/usr/bin/env bash
set -euo pipefail
NS={shlex.quote(namespace)}
REL={shlex.quote(release)}
CHART=/command-files/{shlex.quote(chart_tgz.name)}
VALS=/command-files/{shlex.quote(values_file.name)}

kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install "$REL" "$CHART" \
  --namespace "$NS" \
  --create-namespace \
  -f "$VALS" \
  --timeout=15m \
  --wait \
  --debug || INSTALL_ERR=$?

if [ -n "${{INSTALL_ERR:-}}" ]; then
  echo "--- Status ---"; helm -n "$NS" status "$REL" || true
  echo "--- Pods ---"; kubectl -n "$NS" get pods || true
  echo "--- Events ---"; kubectl -n "$NS" get events --sort-by='.lastTimestamp' | tail -20 || true
  exit 1
fi

helm -n "$NS" status "$REL"
kubectl -n "$NS" get pods
"""
    with tempfile.TemporaryDirectory() as t:
        sh = Path(t) / "install.sh"
        sh.write_text(script, encoding="utf-8")
        out = aks_invoke(
            resource_group,
            cluster_name,
            f"bash {sh.name}",
            files=[sh, chart_tgz, values_file],
        )
        return out
