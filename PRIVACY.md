# MiniDataDev beta privacy notice

MiniDataDev is local-first. Uploaded datasets, saved projects, conversations,
and operational event logs are stored under the configured local
`.minidatadev` directory. They are not uploaded by the application in Demo
mode.

When a hosted AI provider is selected, the application may send bounded
dataset context, including column names, profile statistics, and preview rows,
to that provider to answer a question. MiniDataDev never gives the model
arbitrary code execution.

Users can delete individual projects or purge projects older than the
configured retention period from **Projects & export**. Removing a project
deletes its local dataset copy and saved conversation metadata.

Do not upload confidential or regulated data unless the chosen deployment,
AI provider, access controls, and organizational policies have been reviewed
for that use.
