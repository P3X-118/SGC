<!--
SPDX-FileCopyrightText: 2025 SGC contributors

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# AWX

The playbook can install and configure [AWX](https://github.com/ansible/awx) for you.

AWX provides a web-based user interface, REST API, and task engine built on top of Ansible. It is the upstream project for Red Hat Ansible Automation Platform.

## Dependencies

This service requires the following other services:

- [Postgres](postgres.md) database
- [Traefik](traefik.md) reverse-proxy server

## Adjusting the playbook configuration

To enable this service, add the following configuration to your `vars.yml` file and re-run the [installation](../installing.md) process:

```yaml
########################################################################
#                                                                      #
# awx                                                                   #
#                                                                      #
########################################################################

awx_enabled: true

awx_hostname: awx.example.com

awx_admin_user: admin
awx_admin_password: "your-secure-password-here"

awx_secret_key: "your-django-secret-key-here"

########################################################################
#                                                                      #
# /awx                                                                  #
#                                                                      #
########################################################################
```

### Configuration Options

The following are notable configuration options:

- `awx_hostname` - The hostname at which AWX will be served (required for Traefik)
- `awx_admin_user` - The default admin username (default: `admin`)
- `awx_admin_password` - The admin password (required, should be a strong password)
- `awx_secret_key` - Django secret key for session encryption (auto-generated if not provided)
- `awx_broadcast_websocket_secret` - WebSocket secret for real-time updates (auto-generated if not provided)

### Redis Configuration

AWX requires Redis for the task queue. The role automatically creates a dedicated Redis container:

- `awx_redis_enabled` - Enable dedicated Redis for AWX (default: `true`)
- `awx_redis_version` - Redis version (default: `8.4.0`)

### Receptor/Task Worker Configuration

AWX runs with a receptor task worker for executing Ansible jobs:

- `awx_receptor_enabled` - Enable receptor worker (default: `true`)

### Projects Storage

AWX stores Ansible playbooks and project files:

- `awx_projects_storage_kind` - Storage type (default: `volume`)
- `awx_projects_storage_path` - Path on host (default: `/awx/projects`)

### Container Image

By default, AWX uses the official Docker Hub image. To use a custom image:

```yaml
awx_container_image_registry_prefix: "your-registry.example.com/"
awx_container_image_tag: "your-custom-version"
```

## Usage

After installation, the AWX instance becomes available at the URL specified with `awx_hostname`. With the configuration above, the service is hosted at `https://awx.example.com`.

To get started:

1. Navigate to `https://awx.example.com`
2. Log in with the admin credentials you configured
3. Create your first organization, credential, and project
4. Run your first job template

## Security Considerations

The role configures AWX with the following security headers by default:

- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-XSS-Protection: 1; mode=block` - XSS filter
- `Content-Security-Policy: frame-anscestors 'self'` - Prevents embedding

## Backup

Ensure you backup:

- `/awx` - AWX data directory (includes projects, secret keys)
- Your PostgreSQL database containing AWX data
