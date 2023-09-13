# syntax=docker/dockerfile:1
# Use Jupyter base image
FROM jupyter/base-notebook

RUN rm /home/jovyan/.jupyter/jupyter_notebook_config.py
COPY . /home/jovyan/.jupyter

# Add Tini. Tini operates as a process subreaper for jupyter. This prevents
# kernel crashes.
#USER root
#ENV TINI_VERSION v0.18.0
#ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /usr/bin/tini
#RUN chmod +x /usr/bin/tini
#ENTRYPOINT ["/usr/bin/tini", "--"]
#USER $NB_UID

EXPOSE 8000

CMD ["jupyter", "notebook"]