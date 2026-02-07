# Victim container: "Primary Doctor" workstation simulation
# Educational demo only - simulates a device that can be compromised via malicious email
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Simulated inbox: "malicious" attachment lives here (delivered by "email")
COPY payload/ /app/inbox/
# Script that simulates opening the email attachment
COPY scripts/ /app/scripts/
# Web-based GUI for the workstation (email client)
COPY webapp/ /app/webapp/
RUN pip install --no-cache-dir -r /app/webapp/requirements.txt \
    && chmod +x /app/scripts/open_email_attachment.sh /app/inbox/patient_lab_results.pdf.py

# Doctor workstation simulation - show it's a "medical" context
ENV USER=dr_smith
ENV ROLE=primary_physician

# Serve the web GUI on 8080
EXPOSE 8080
CMD ["python3", "/app/webapp/app.py"]
