FROM ubuntu:26.04 AS native
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 ROS_DISTRO=lyrical
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY docker/install-stack.sh /tmp/install-stack.sh
RUN bash /tmp/install-stack.sh && rm /tmp/install-stack.sh
ARG USER_UID=1000
ARG USER_GID=1000
# Ubuntu base images reserve UID 1000 for their default user.
RUN if id ubuntu &>/dev/null; then userdel -r ubuntu; fi \
    && test "$USER_UID" -gt 0 && test "$USER_GID" -gt 0 \
    && (getent group "$USER_GID" || groupadd -g "$USER_GID" user) \
    && useradd -m -s /bin/bash -u "$USER_UID" -g "$USER_GID" user \
    && echo 'user ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/developer \
    && chmod 440 /etc/sudoers.d/developer
ENV HOME=/home/user
COPY docker/bashrc /etc/ros-workshop.bashrc
COPY docker/source-workspaces.bash /etc/ros-workshop-workspaces.bash
COPY docker/entrypoint.sh /usr/local/bin/ros-entrypoint
COPY --chown=user docker/tmux.conf /home/user/.tmux.conf
COPY --chown=user docker/vimrc /home/user/.vimrc
COPY docker/install-user-config.sh /usr/local/bin/install-workshop-user-config
COPY --chown=user docker/rviz-persistent-settings /home/user/.rviz2/persistent_settings
COPY docker/rviz-persistent-settings /etc/ros-workshop-rviz-settings
COPY --chown=user Projects /home/user/Projects
COPY docker/build-ardrone-workspace.sh /tmp/build-ardrone-workspace.sh
RUN bash /tmp/build-ardrone-workspace.sh && rm /tmp/build-ardrone-workspace.sh
COPY --chown=user Commands/bin /home/user/bin
RUN mkdir -p "$HOME/Data" "$HOME/ExampleCode" \
    && echo 'source /etc/ros-workshop.bashrc' >> "$HOME/.bashrc" \
    && echo 'source "$HOME/.bashrc"' > "$HOME/.bash_profile" \
    && chown -R user:"$(id -gn user)" "$HOME"
USER user
RUN /usr/local/bin/install-workshop-user-config
WORKDIR /home/user
ENTRYPOINT ["/usr/local/bin/ros-entrypoint"]
CMD ["bash"]

FROM native AS vnc
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal dbus-x11 tigervnc-standalone-server tigervnc-tools novnc websockify x11-utils tini \
    && rm -rf /var/lib/apt/lists/*
COPY docker/fonts /usr/local/share/fonts/cascadia
RUN fc-cache -f
COPY --chown=user docker/xfce-terminalrc /home/user/.config/xfce4/terminal/terminalrc
COPY docker/start-vnc.sh /usr/local/bin/start-workshop-vnc
USER user
ENV DISPLAY=:1
EXPOSE 5901 6901
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/ros-entrypoint"]
CMD ["/usr/local/bin/start-workshop-vnc"]
