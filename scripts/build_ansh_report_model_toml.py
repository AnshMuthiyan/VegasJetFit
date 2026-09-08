import argparse
import json
from pathlib import Path


MODEL_NAME_DEFAULT = "PowerlawJetVegasDylanSpectrumModel"


def fmt(value):
    if isinstance(value, str):
        return f"'{value}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return repr(value)


def mapped_name(plugin: str, name: str) -> str:
    if plugin == "source_frame_dust" and name == "Ebv":
        return "ebv_source_frame"
    if plugin == "milky_way_dust" and name == "Ebv":
        return "ebv_milky_way"
    if plugin == "afterglow_flux" and name == "dL28":
        return "dl28"
    return name


def write_uniform_block(lines, table_name: str, param_name: str, scale: str, prior: dict):
    lines.append(f"[[{table_name}]]")
    lines.append(f"name = {fmt(param_name)}")
    lines.append(f"scale = {fmt(scale)}")
    lines.append("")
    lines.append(f"[{table_name}.prior]")
    lines.append("type = 'uniform'")
    lines.append(f"lower = {fmt(prior['lower'])}")
    lines.append(f"upper = {fmt(prior['upper'])}")
    if prior.get("initial_guess") is not None:
        lines.append(f"initial_guess = {fmt(prior['initial_guess'])}")
    if prior.get("initial_sigma") is not None:
        lines.append(f"initial_sigma = {fmt(prior['initial_sigma'])}")
    lines.append("")


def write_gaussian_block(lines, table_name: str, param_name: str, scale: str, prior: dict):
    lines.append(f"[[{table_name}]]")
    lines.append(f"name = {fmt(param_name)}")
    lines.append(f"scale = {fmt(scale)}")
    lines.append("")
    lines.append(f"[{table_name}.prior]")
    lines.append("type = 'gaussian'")
    lines.append(f"mu = {fmt(prior['mu'])}")
    lines.append(f"sigma = {fmt(prior['sigma'])}")
    if prior.get("initial_guess") is not None:
        lines.append(f"initial_guess = {fmt(prior['initial_guess'])}")
    if prior.get("initial_sigma") is not None:
        lines.append(f"initial_sigma = {fmt(prior['initial_sigma'])}")
    lines.append("")


def write_value_block(lines, table_name: str, param_name: str, scale: str, value):
    lines.append(f"[[{table_name}]]")
    lines.append(f"name = {fmt(param_name)}")
    lines.append(f"scale = {fmt(scale)}")
    lines.append(f"value = {fmt(value)}")
    lines.append("")


def main():
    parser = argparse.ArgumentParser(description="Build a JetFit model TOML from Ansh report.json metadata.")
    parser.add_argument("--report", required=True, help="Path to Ansh report.json")
    parser.add_argument("--output", required=True, help="Output model TOML path")
    parser.add_argument("--model-name", default=MODEL_NAME_DEFAULT, help="JetFit model class name")
    args = parser.parse_args()

    report_path = Path(args.report).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    report = json.loads(report_path.read_text())

    lines: list[str] = [f"name = {fmt(args.model_name)}", ""]

    for param in report["inference"]["params"]:
        plugin = param["plugin"]
        stage = param["stage"]
        name = mapped_name(plugin, param["name"])

        if plugin == "afterglow_flux":
            table_name = "model"
        elif plugin in {"source_frame_dust", "milky_way_dust"}:
            table_name = "extinction"
        elif plugin == "calibration":
            table_name = "offsets"
        elif plugin == "chi_squared":
            table_name = "slop"
        else:
            raise ValueError(f"Unsupported plugin: {plugin}")

        if plugin in {"source_frame_dust", "milky_way_dust"} and param["name"] == "Rv":
            continue
        if plugin == "source_frame_dust" and param["name"] == "z":
            continue

        scale = param.get("infer_scale", "linear")
        prior = param.get("prior")
        if prior is not None:
            if "mu" in prior:
                write_gaussian_block(lines, table_name, name, scale, prior)
            else:
                write_uniform_block(lines, table_name, name, scale, prior)
            continue

        if stage == "init":
            value = param["value"]
        elif stage == "eval":
            value = param["value"]
        else:
            raise ValueError(f"Unsupported stage: {stage}")

        write_value_block(lines, table_name, name, scale, value)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n")
    print(output_path)


if __name__ == "__main__":
    main()
