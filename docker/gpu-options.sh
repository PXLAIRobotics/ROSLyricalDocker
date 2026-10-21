# Sourced by VNC launchers; adds to their Docker argument array.
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    runtimes=$(docker info --format '{{range $name, $runtime := .Runtimes}}{{$name}} {{end}}')
    if [[ " $runtimes " == *" nvidia "* ]]; then
        args+=(--runtime=nvidia --gpus all -e NVIDIA_DRIVER_CAPABILITIES=graphics,display,utility,compute)
        args+=(-e __GLX_VENDOR_LIBRARY_NAME=nvidia -e __NV_PRIME_RENDER_OFFLOAD=1)
    else
        args+=(-e LIBGL_ALWAYS_SOFTWARE=1)
    fi
elif [[ -d /dev/dri ]]; then
    args+=(--device=/dev/dri)
    for device in /dev/dri/*; do
        [[ ! -c "$device" ]] || args+=(--group-add="$(stat -c %g "$device")")
    done
fi
