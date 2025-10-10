FROM semtech/mu-python-template:2.0.0-beta.3
LABEL maintainer="you@example.com"

# Install spaCy models for Dutch, German, and English
RUN python -m spacy download nl_core_news_sm
RUN python -m spacy download de_core_news_sm  
RUN python -m spacy download en_core_web_sm