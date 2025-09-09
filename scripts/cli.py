from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

from .utils import (
    CmdError,
    aks_invoke,
    apply_yaml_via_b64,
    apply_files_server_side,
    ensure_eso,
    grant_kubelet_kv_role,
    install_chart_server_side,
    package_chart_from_zip,
    upsert_kv_secret,
    cdktf,
    ensure_namespace,
    install_ingress_nginx,
    annotate_ingress_internal,
    helm_list_all,
    kubectl_get,
    kubectl_get_text,
    run as run_cmd,
)


ZIP_URL = "https://github.com/supabase-community/supabase-kubernetes/archive/refs/heads/main.zip"


def load_file(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def sync_keyvault_secrets(
    kv: str,
    rg: str,
    aks: str,
    secrets_file: Path | None,
    generate_defaults: bool,
    skip_role_assignment: bool,
) -> None:
    # Grant RBAC first (optional) so kubelet MI can read Key Vault
    if not skip_role_assignment and rg and aks and kv:
        try:
            grant_kubelet_kv_role(resource_group=rg, cluster_name=aks, kv_name=kv)
        except CmdError as e:
            print("WARNING: Failed to assign 'Key Vault Secrets User' to kubelet identity.")
            print("Proceeding to sync secrets, but ESO may 403 until RBAC is granted.")
            print(str(e))
    # load secrets map
    data: Dict[str, str] = {}
    if secrets_file and secrets_file.exists():
        loaded = json.loads(load_file(secrets_file))
        data = {str(k): str(v) for k, v in loaded.items()}
    if generate_defaults or not data:
        # Provide safe defaults for demo; callers should override for production
        data.setdefault("jwt-secret", os.urandom(48).hex())
        data.setdefault("anon-key", os.urandom(48).hex())
        data.setdefault("service-role-key", os.urandom(48).hex())
        data.setdefault(
            "postgres-connection-string",
            "postgresql://postgres:postgres@supabase-supabase-db:5432/postgres",
        )
        # S3 client creds used by Supabase when calling S3 proxy
        data.setdefault(
            "supabase-storage-creds", '{"keyId":"access","accessKey":"secret"}'
        )
    # Ensure Azure Storage credentials exist; if not, try to resolve from the resource group
    if (
        "azure-storage-account-name" not in data
        or "azure-storage-account-key" not in data
    ):
        if rg:
            try:
                # pick first storage account in RG (or tailor by name prefix if needed)
                import subprocess, json as _json

                name = subprocess.check_output(
                    [
                        "az",
                        "storage",
                        "account",
                        "list",
                        "-g",
                        rg,
                        "--query",
                        "[0].name",
                        "-o",
                        "tsv",
                    ],
                    text=True,
                ).strip()
                if name:
                    key = subprocess.check_output(
                        [
                            "az",
                            "storage",
                            "account",
                            "keys",
                            "list",
                            "-n",
                            name,
                            "-g",
                            rg,
                            "--query",
                            "[0].value",
                            "-o",
                            "tsv",
                        ],
                        text=True,
                    ).strip()
                    if key:
                        data.setdefault("azure-storage-account-name", name)
                        data.setdefault("azure-storage-account-key", key)
            except Exception:
                pass
    if (
        "azure-storage-account-name" not in data
        or "azure-storage-account-key" not in data
    ):
        raise CmdError(
            "Missing Azure Storage credentials: provide 'azure-storage-account-name' and 'azure-storage-account-key' via --secrets-file or ensure Azure CLI can list keys in the resource group."
        )
    # Derive Azure Storage connection string for ExternalSecret compatibility if absent
    if "storage-connection-string" not in data:
        name = data.get("azure-storage-account-name", "")
        key = data.get("azure-storage-account-key", "")
        if name and key:
            data["storage-connection-string"] = (
                f"DefaultEndpointsProtocol=https;AccountName={name};AccountKey={key};EndpointSuffix=core.windows.net"
            )
    # upsert secrets
    for name, value in data.items():
        if not value:
            raise CmdError(f"Secret '{name}' has empty value")
        upsert_kv_secret(kv, name, value)


def secrets_sync(args: argparse.Namespace) -> None:
    kv = args.key_vault
    rg = args.resource_group or ""
    aks = args.cluster_name or ""
    secrets_file = Path(args.secrets_file).resolve() if args.secrets_file else None
    generate = bool(args.generate_default_secrets)
    skip_rbac = bool(getattr(args, "skip_role_assignment", False))
    sync_keyvault_secrets(
        kv=kv,
        rg=rg,
        aks=aks,
        secrets_file=secrets_file,
        generate_defaults=generate,
        skip_role_assignment=skip_rbac,
    )


def apply_eso(rg: str, aks: str, manifest_paths: list[Path]) -> None:
    files = [p for p in manifest_paths if p.exists()]
    if files:
        apply_files_server_side(rg, aks, files)


def deploy(args: argparse.Namespace) -> None:
    rg = args.resource_group
    aks = args.cluster_name
    ns = args.namespace
    kv = args.key_vault
    values = Path(args.values_file).resolve()
    release = args.release
    secrets_file = Path(args.secrets_file).resolve() if args.secrets_file else None
    generate_defaults = bool(args.generate_default_secrets)

    if not values.exists():
        raise CmdError(f"Values file not found: {values}")

    # 1) Ensure ESO on cluster
    ensure_eso(resource_group=rg, cluster_name=aks)

    # 2) Sync KV secrets and grant RBAC
    sync_keyvault_secrets(
        kv=kv,
        rg=rg,
        aks=aks,
        secrets_file=secrets_file,
        generate_defaults=generate_defaults,
    )

    # 3) Apply ESO manifests
    manifests = [
        Path("k8s/eso/secretstore.yaml"),
        Path("k8s/eso/externalsecret.yaml"),
        Path("k8s/eso/storage-externalsecret.yaml"),
        Path("k8s/eso/azure-storage-externalsecret.yaml"),
        Path("k8s/s3proxy/deployment.yaml"),
    ]
    for m in manifests:
        if not m.exists():
            raise CmdError(f"Manifest missing: {m}")
    apply_eso(rg=rg, aks=aks, manifest_paths=manifests)

    # 4) Package chart from GitHub ZIP (avoids Windows symlink extraction issues)
    chart_tgz = package_chart_from_zip(ZIP_URL)

    # 5) Install on AKS server-side Helm
    out = install_chart_server_side(
        resource_group=rg,
        cluster_name=aks,
        namespace=ns,
        release=release,
        chart_tgz=chart_tgz,
        values_file=values,
    )
    print(out)


def infra_deploy(args: argparse.Namespace) -> None:
    project = Path(args.project_dir)
    if not project.exists():
        raise CmdError(f"Project directory not found: {project}")
    print("Synthesizing CDKTF...")
    cdktf(project, ["get"])  # ensure providers
    cdktf(project, ["synth"])  # generate JSON tf
    print("Deploying CDKTF...")
    cdktf(project, ["deploy", "--auto-approve"])
    print("CDKTF deploy completed.")


def infra_destroy(args: argparse.Namespace) -> None:
    project = Path(args.project_dir)
    if not project.exists():
        raise CmdError(f"Project directory not found: {project}")
    print("Destroying CDKTF-managed infrastructure...")
    cdktf(project, ["destroy", "--auto-approve"])
    print("Destroy completed.")


def aks_configure(args: argparse.Namespace) -> None:
    rg = args.resource_group
    aks = args.cluster_name
    ns = args.namespace
    print(f"Configuring AKS {rg}/{aks}...")
    ensure_namespace(rg, aks, ns)
    ensure_eso(rg, aks)
    install_ingress_nginx(rg, aks)
    annotate_ingress_internal(rg, aks)
    # Apply ESO baseline manifests
    eso_files = [
        Path("k8s/eso/secretstore.yaml"),
        Path("k8s/eso/externalsecret.yaml"),
        Path("k8s/eso/storage-externalsecret.yaml"),
        Path("k8s/eso/azure-storage-externalsecret.yaml"),
        Path("k8s/eso/db-externalsecret.yaml"),
        Path("k8s/s3proxy/deployment.yaml"),
    ]
    apply_eso(rg, aks, eso_files)

    # Apply baseline policies
    files = [
        Path("k8s/hpa/postgrest-hpa.yaml"),
        Path("k8s/hpa/realtime-hpa.yaml"),
        Path("k8s/networkpolicy/supabase-networkpolicy.yaml"),
    ]
    apply_files_server_side(rg, aks, [f for f in files if f.exists()])
    print("AKS baseline configuration complete.")


def diagnose(args: argparse.Namespace) -> None:
    rg = args.resource_group
    aks = args.cluster_name
    ns = args.namespace
    release = args.release
    print("=== Supabase Deployment Diagnostics ===")
    # cluster status
    try:
        info = json.loads(
            run_cmd(
                [
                    "az",
                    "aks",
                    "show",
                    "-g",
                    rg,
                    "-n",
                    aks,
                    "--query",
                    "{name:name, powerState:powerState.code, provisioningState:provisioningState, kubernetesVersion:kubernetesVersion}",
                    "-o",
                    "json",
                ]
            )
        )
        print(
            f"AKS: {info['name']} | Power: {info['powerState']} | State: {info['provisioningState']} | K8s: {info['kubernetesVersion']}"
        )
    except Exception as e:
        print(f"AKS info error: {e}")
    # helm releases
    try:
        releases_raw = helm_list_all(rg, aks)
        releases = json.loads(releases_raw) if releases_raw else []
        target = [
            r for r in releases if r.get("name") == release and r.get("namespace") == ns
        ]
        if target:
            r = target[0]
            print(
                f"Release {release} in {ns}: {r.get('status')} | chart {r.get('chart')} rev {r.get('revision')}"
            )
        else:
            print(f"Release {release} not found in {ns}.")
    except Exception as e:
        print(f"helm list error: {e}")
    # pods
    try:
        pods = json.loads(kubectl_get(rg, aks, ns, "pods"))
        count = len(pods.get("items", []))
        print(f"Pods in {ns}: {count}")
        for p in pods.get("items", [])[:10]:
            name = p["metadata"]["name"]
            phase = p["status"].get("phase")
            print(f"  {name}: {phase}")
    except Exception as e:
        print(f"pods error: {e}")
    # ESO
    try:
        eso_txt = kubectl_get_text(rg, aks, ns, "secretstore,externalsecret")
        print(eso_txt)
    except Exception:
        pass
    # events
    try:
        events = aks_invoke(
            rg, aks, f"kubectl -n {ns} get events --sort-by='.lastTimestamp' | tail -20"
        )
        print("Recent events:\n" + events)
    except Exception:
        pass


def smoke_test(args: argparse.Namespace) -> None:
    rg = args.resource_group
    aks = args.cluster_name
    base = args.base_url
    internal = bool(args.internal)
    if internal:
        # Simplest reliable approach: create a short-lived Pod with the supabase label, exec curl, then delete the Pod.
        http_cmd = (
            "bash -lc '"
            'set -e; '
            # Resolve Kong service name dynamically (release-dependent); fallback to legacy kong-proxy.
            'KONG=$(kubectl -n supabase get svc -l app.kubernetes.io/name=supabase-kong -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || true); '
            'if [ -z "$KONG" ]; then '
            '  KONG=$(kubectl -n supabase get svc -o jsonpath="{range .items[*]}{.metadata.name}{'"'"'\n'"'"'}{end}" | grep -i kong | head -n1 || true); '
            'fi; '
            '[ -n "$KONG" ] || KONG=kong-proxy; '
            'PORT=$(kubectl -n supabase get svc "$KONG" -o jsonpath="{.spec.ports[?(@.name==\"http\")].port}" 2>/dev/null); '
            '[ -n "$PORT" ] || PORT=$(kubectl -n supabase get svc "$KONG" -o jsonpath="{.spec.ports[0].port}" 2>/dev/null || echo 80); '
            'BASE="http://$KONG.supabase.svc.cluster.local:${PORT}/rest/v1/"; '
            'POD=curlpod-$(date +%s); '
            'kubectl -n supabase delete pod "$POD" --ignore-not-found >/dev/null 2>&1 || true; '
            'cat > /tmp/"$POD".yaml <<EOF\n'
            'apiVersion: v1\n'
            'kind: Pod\n'
            'metadata:\n'
            '  name: '"$POD"'\n'
            '  namespace: supabase\n'
            '  labels:\n'
            '    app.kubernetes.io/part-of: supabase\n'
            '    app: curltest\n'
            'spec:\n'
            '  restartPolicy: Never\n'
            '  containers:\n'
            '  - name: curl\n'
            '    image: curlimages/curl\n'
            '    command: ["sh","-c","sleep 3600"]\n'
            'EOF\n'
            'kubectl apply -f /tmp/"$POD".yaml >/dev/null; '
            'kubectl -n supabase wait --for=condition=Ready pod/"$POD" --timeout=120s || true; '
            'ANON=$(kubectl -n supabase get secret supabase-env -o jsonpath="{.data.ANON_KEY}" 2>/dev/null | base64 -d || true); '
            'if [ -n "$ANON" ]; then '
            '  OUT=$(kubectl -n supabase exec "$POD" -- sh -lc "curl -sS -o /dev/null -w CODE:%{http_code}\\n -H \"apikey: ${ANON}\" -H \"Authorization: Bearer ${ANON}\" $BASE "); '
            'else '
            '  OUT=$(kubectl -n supabase exec "$POD" -- sh -lc "curl -sS -o /dev/null -w CODE:%{http_code}\\n $BASE "); '
            'fi; '
            'echo "$OUT"; '
            'kubectl -n supabase delete pod "$POD" --ignore-not-found >/dev/null 2>&1 || true'
            "'"
        )
        logs = aks_invoke(rg, aks, http_cmd)
        print(logs)
        return
    # external: auto-detect ingress IP if base not provided
    if not base:
        try:
            ip = aks_invoke(
                rg,
                aks,
                "kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'",
            )
            ip = ip.strip("'\"")
            if not ip:
                raise CmdError("No ingress IP found")
            base = f"http://{ip}.nip.io"
        except Exception as e:
            raise CmdError(f"Failed to detect Ingress IP: {e}")
    import urllib.request

    url = base.rstrip("/") + "/rest/v1/"
    print(f"Testing {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"HTTP {resp.status}")
        if resp.status != 200:
            raise CmdError(f"Unexpected code: {resp.status}")


def deploy_chart(args: argparse.Namespace) -> None:
    rg = args.resource_group
    aks = args.cluster_name
    ns = args.namespace
    release = args.release
    tgz = Path(args.chart_tgz).resolve()
    values = Path(args.values_file).resolve()
    if not tgz.exists():
        raise CmdError(f"Chart package not found: {tgz}")
    if not values.exists():
        raise CmdError(f"Values file not found: {values}")

    out = install_chart_server_side(
        resource_group=rg,
        cluster_name=aks,
        namespace=ns,
        release=release,
        chart_tgz=tgz,
        values_file=values,
    )
    print(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="supabase-deployer", description="Supabase AKS deployment CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("deploy", help="Deploy Supabase to AKS")
    d.add_argument("--resource-group", required=True)
    d.add_argument("--cluster-name", required=True)
    d.add_argument("--namespace", required=True)
    d.add_argument("--key-vault", required=True)
    d.add_argument("--values-file", required=True)
    d.add_argument("--release", required=True)
    d.add_argument("--secrets-file")
    d.add_argument("--generate-default-secrets", action="store_true")
    d.set_defaults(func=deploy)

    idep = sub.add_parser("infra-deploy", help="Deploy infrastructure via CDKTF")
    idep.add_argument("--project-dir", default="infra")
    idep.set_defaults(func=infra_deploy)

    ides = sub.add_parser("infra-destroy", help="Destroy infrastructure via CDKTF")
    ides.add_argument("--project-dir", default="infra")
    ides.set_defaults(func=infra_destroy)

    aksc = sub.add_parser(
        "aks-configure", help="Configure AKS baseline (NS, ESO, Ingress, HPAs)"
    )
    aksc.add_argument("--resource-group", required=True)
    aksc.add_argument("--cluster-name", required=True)
    aksc.add_argument("--namespace", default="supabase")
    aksc.set_defaults(func=aks_configure)

    diag = sub.add_parser("diagnose", help="Diagnose deployment status")
    diag.add_argument("--resource-group", required=True)
    diag.add_argument("--cluster-name", required=True)
    diag.add_argument("--namespace", default="supabase")
    diag.add_argument("--release", default="supabase")
    diag.set_defaults(func=diagnose)

    smk = sub.add_parser("smoke-test", help="Run smoke test")
    smk.add_argument("--resource-group")
    smk.add_argument("--cluster-name")
    smk.add_argument("--base-url")
    smk.add_argument("--internal", action="store_true")
    smk.set_defaults(func=smoke_test)

    sec = sub.add_parser(
        "secrets-sync", help="Sync application secrets to Azure Key Vault"
    )
    sec.add_argument("--key-vault", required=True)
    sec.add_argument("--resource-group")
    sec.add_argument("--cluster-name")
    sec.add_argument("--secrets-file")
    sec.add_argument("--generate-default-secrets", action="store_true")
    sec.add_argument(
        "--skip-role-assignment",
        action="store_true",
        help="Skip assigning 'Key Vault Secrets User' to the kubelet Managed Identity",
    )
    sec.set_defaults(func=secrets_sync)

    dloc = sub.add_parser(
        "deploy-chart", help="Deploy a pre-packaged Supabase Helm chart (.tgz)"
    )
    dloc.add_argument("--resource-group", required=True)
    dloc.add_argument("--cluster-name", required=True)
    dloc.add_argument("--namespace", required=True)
    dloc.add_argument("--release", required=True)
    dloc.add_argument("--chart-tgz", required=True, help="Path to supabase-*.tgz")
    dloc.add_argument("--values-file", required=True)
    dloc.set_defaults(func=deploy_chart)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
