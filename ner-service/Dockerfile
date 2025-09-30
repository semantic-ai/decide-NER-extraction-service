FROM semtech/mu-python-template:2.0.0-beta.3
LABEL maintainer="you@example.com"

# Remove existing ext directory if it exists to avoid conflict, then recreate the symbolic link
RUN rm -rf /usr/src/app/ext && ln -s /app /usr/src/app/ext

# Install spaCy models for Dutch, German, and English
RUN python -m spacy download nl_core_news_sm && \
    python -m spacy download de_core_news_sm && \
    python -m spacy download en_core_web_sm