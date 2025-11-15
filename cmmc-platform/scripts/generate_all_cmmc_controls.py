#!/usr/bin/env python3
"""
Generate Complete CMMC Level 2 Controls SQL Seed File
Creates all 110 NIST SP 800-171 Rev 2 controls for CMMC Level 2

Based on:
- NIST SP 800-171 Revision 2
- CMMC Level 2 Assessment Guide Version 2.13
"""

# Complete mapping of all 110 CMMC Level 2 controls
# Organized by 14 domains matching NIST SP 800-171

CMMC_L2_CONTROLS = {
    # ACCESS CONTROL (AC) - 22 controls
    "AC": [
        ("AC.L2-3.1.1", "3.1.1", "Limit System Access to Authorized Users",
         "Limit information system access to authorized users, processes acting on behalf of authorized users, or devices (including other information systems)."),

        ("AC.L2-3.1.2", "3.1.2", "Limit System Access to Transaction Types",
         "Limit information system access to the types of transactions and functions that authorized users are permitted to execute."),

        ("AC.L2-3.1.3", "3.1.3", "Control Flow of CUI",
         "Control the flow of CUI in accordance with approved authorizations."),

        ("AC.L2-3.1.4", "3.1.4", "Separation of Duties",
         "Separate the duties of individuals to reduce the risk of malevolent activity without collusion."),

        ("AC.L2-3.1.5", "3.1.5", "Principle of Least Privilege",
         "Employ the principle of least privilege, including for specific security functions and privileged accounts."),

        ("AC.L2-3.1.6", "3.1.6", "Non-Privileged Account Use",
         "Use non-privileged accounts or roles when accessing nonsecurity functions."),

        ("AC.L2-3.1.7", "3.1.7", "Privileged Functions",
         "Prevent non-privileged users from executing privileged functions and audit the execution of such functions."),

        ("AC.L2-3.1.8", "3.1.8", "Unsuccessful Logon Attempts",
         "Limit unsuccessful logon attempts."),

        ("AC.L2-3.1.9", "3.1.9", "Privacy and Security Notices",
         "Provide privacy and security notices consistent with applicable CUI rules."),

        ("AC.L2-3.1.10", "3.1.10", "Session Lock",
         "Use session lock with pattern-hiding displays to prevent access and viewing of data after a period of inactivity."),

        ("AC.L2-3.1.11", "3.1.11", "Session Termination",
         "Terminate (automatically) a user session after a defined condition."),

        ("AC.L2-3.1.12", "3.1.12", "Control Remote Access",
         "Monitor and control remote access sessions."),

        ("AC.L2-3.1.13", "3.1.13", "Cryptographic Mechanisms for Remote Access",
         "Employ cryptographic mechanisms to protect the confidentiality of remote access sessions."),

        ("AC.L2-3.1.14", "3.1.14", "Route Remote Access",
         "Route remote access via managed access control points."),

        ("AC.L2-3.1.15", "3.1.15", "Authorize Remote Access",
         "Authorize remote execution of privileged commands and remote access to security-relevant information."),

        ("AC.L2-3.1.16", "3.1.16", "Authorize Wireless Access",
         "Authorize wireless access prior to allowing such connections."),

        ("AC.L2-3.1.17", "3.1.17", "Protect Wireless Access",
         "Protect wireless access using authentication and encryption."),

        ("AC.L2-3.1.18", "3.1.18", "Control Connection of Mobile Devices",
         "Control connection of mobile devices."),

        ("AC.L2-3.1.19", "3.1.19", "Encrypt CUI on Mobile Devices",
         "Encrypt CUI on mobile devices and mobile computing platforms."),

        ("AC.L2-3.1.20", "3.1.20", "External Connections",
         "Verify and control/limit connections to and use of external information systems."),

        ("AC.L2-3.1.21", "3.1.21", "Portable Storage Devices",
         "Limit use of organizational portable storage devices on external information systems."),

        ("AC.L2-3.1.22", "3.1.22", "Control CUI Posting",
         "Control CUI posted or processed on publicly accessible information systems."),
    ],

    # AWARENESS AND TRAINING (AT) - 3 controls
    "AT": [
        ("AT.L2-3.2.1", "3.2.1", "Security Awareness",
         "Ensure that managers, systems administrators, and users of organizational information systems are made aware of the security risks associated with their activities and of the applicable policies, standards, and procedures related to the security of those systems."),

        ("AT.L2-3.2.2", "3.2.2", "Insider Threat Awareness",
         "Ensure that personnel are trained to carry out their assigned information security-related duties and responsibilities."),

        ("AT.L2-3.2.3", "3.2.3", "Security Training Records",
         "Provide security awareness training on recognizing and reporting potential indicators of insider threat."),
    ],

    # AUDIT AND ACCOUNTABILITY (AU) - 9 controls
    "AU": [
        ("AU.L2-3.3.1", "3.3.1", "System Audit Logs",
         "Create, protect, and retain information system audit records to the extent needed to enable monitoring, analysis, investigation, and reporting of unlawful, unauthorized, or inappropriate information system activity."),

        ("AU.L2-3.3.2", "3.3.2", "User Accountability",
         "Ensure that the actions of individual information system users can be uniquely traced to those users so they can be held accountable for their actions."),

        ("AU.L2-3.3.3", "3.3.3", "Audit Record Review",
         "Review and update logged events."),

        ("AU.L2-3.3.4", "3.3.4", "Alert Generation",
         "Alert in the event of an audit logging process failure."),

        ("AU.L2-3.3.5", "3.3.5", "Correlate Audit Records",
         "Correlate audit record review, analysis, and reporting processes for investigation and response to indications of unlawful, unauthorized, suspicious, or unusual activity."),

        ("AU.L2-3.3.6", "3.3.6", "Audit Reduction",
         "Provide audit record reduction and report generation to support on-demand analysis and reporting."),

        ("AU.L2-3.3.7", "3.3.7", "Time Stamps",
         "Provide a system capability that compares and synchronizes internal information system clocks with an authoritative source to generate time stamps for audit records."),

        ("AU.L2-3.3.8", "3.3.8", "Protect Audit Information",
         "Protect audit information and audit logging tools from unauthorized access, modification, and deletion."),

        ("AU.L2-3.3.9", "3.3.9", "Limit Audit Log Management",
         "Limit management of audit logging functionality to a subset of privileged users."),
    ],

    # CONFIGURATION MANAGEMENT (CM) - 9 controls
    "CM": [
        ("CM.L2-3.4.1", "3.4.1", "Baseline Configuration",
         "Establish and maintain baseline configurations and inventories of organizational information systems (including hardware, software, firmware, and documentation) throughout the respective system development life cycles."),

        ("CM.L2-3.4.2", "3.4.2", "Configuration Change Control",
         "Establish and enforce security configuration settings for information technology products employed in organizational information systems."),

        ("CM.L2-3.4.3", "3.4.3", "Configuration Change Control",
         "Track, review, approve or disapprove, and log changes to organizational information systems."),

        ("CM.L2-3.4.4", "3.4.4", "Security Impact Analysis",
         "Analyze the security impact of changes prior to implementation."),

        ("CM.L2-3.4.5", "3.4.5", "Access Restrictions for Change",
         "Define, document, approve, and enforce physical and logical access restrictions associated with changes to organizational information systems."),

        ("CM.L2-3.4.6", "3.4.6", "Least Functionality",
         "Employ the principle of least functionality by configuring organizational information systems to provide only essential capabilities."),

        ("CM.L2-3.4.7", "3.4.7", "Nonessential Programs",
         "Restrict, disable, or prevent the use of nonessential programs, functions, ports, protocols, and services."),

        ("CM.L2-3.4.8", "3.4.8", "Deny-by-Exception Policy",
         "Apply deny-by-exception (blacklisting) policy to prevent the use of unauthorized software or deny-all, permit-by-exception (whitelisting) policy to allow the execution of authorized software."),

        ("CM.L2-3.4.9", "3.4.9", "User-Installed Software",
         "Control and monitor user-installed software."),
    ],

    # IDENTIFICATION AND AUTHENTICATION (IA) - 11 controls
    "IA": [
        ("IA.L2-3.5.1", "3.5.1", "Identification",
         "Identify information system users, processes acting on behalf of users, or devices."),

        ("IA.L2-3.5.2", "3.5.2", "Authentication",
         "Authenticate (or verify) the identities of those users, processes, or devices, as a prerequisite to allowing access to organizational information systems."),

        ("IA.L2-3.5.3", "3.5.3", "Multifactor Authentication",
         "Use multifactor authentication for local and network access to privileged accounts and for network access to non-privileged accounts."),

        ("IA.L2-3.5.4", "3.5.4", "Replay-Resistant Authentication",
         "Employ replay-resistant authentication mechanisms for network access to privileged and non-privileged accounts."),

        ("IA.L2-3.5.5", "3.5.5", "Prevent Reuse of Identifiers",
         "Prevent reuse of identifiers for a defined period."),

        ("IA.L2-3.5.6", "3.5.6", "Disable Identifiers",
         "Disable identifiers after a defined period of inactivity."),

        ("IA.L2-3.5.7", "3.5.7", "Password Complexity",
         "Enforce a minimum password complexity and change of characters when new passwords are created."),

        ("IA.L2-3.5.8", "3.5.8", "Password Reuse",
         "Prohibit password reuse for a specified number of generations."),

        ("IA.L2-3.5.9", "3.5.9", "Temporary Passwords",
         "Allow temporary password use for system logons with an immediate change to a permanent password."),

        ("IA.L2-3.5.10", "3.5.10", "Cryptographic Protection",
         "Store and transmit only cryptographically-protected passwords."),

        ("IA.L2-3.5.11", "3.5.11", "Obscure Feedback",
         "Obscure feedback of authentication information."),
    ],

    # INCIDENT RESPONSE (IR) - 6 controls
    "IR": [
        ("IR.L2-3.6.1", "3.6.1", "Incident Handling",
         "Establish an operational incident-handling capability for organizational information systems that includes preparation, detection, analysis, containment, recovery, and user response activities."),

        ("IR.L2-3.6.2", "3.6.2", "Incident Reporting",
         "Track, document, and report incidents to designated officials and/or authorities both internal and external to the organization."),

        ("IR.L2-3.6.3", "3.6.3", "Incident Response Testing",
         "Test the organizational incident response capability."),
    ],

    # MAINTENANCE (MA) - 6 controls
    "MA": [
        ("MA.L2-3.7.1", "3.7.1", "Maintenance",
         "Perform maintenance on organizational information systems."),

        ("MA.L2-3.7.2", "3.7.2", "Controlled Maintenance",
         "Provide controls on the tools, techniques, mechanisms, and personnel used to conduct information system maintenance."),

        ("MA.L2-3.7.3", "3.7.3", "Ensure Equipment Removed",
         "Ensure equipment removed for off-site maintenance is sanitized of any CUI."),

        ("MA.L2-3.7.4", "3.7.4", "Check Media for Malicious Code",
         "Check media containing diagnostic and test programs for malicious code before the media are used in organizational information systems."),

        ("MA.L2-3.7.5", "3.7.5", "Nonlocal Maintenance",
         "Require multifactor authentication to establish nonlocal maintenance sessions via external network connections and terminate such connections when nonlocal maintenance is complete."),

        ("MA.L2-3.7.6", "3.7.6", "Supervise Maintenance Personnel",
         "Supervise the maintenance activities of maintenance personnel without required access authorization."),
    ],

    # MEDIA PROTECTION (MP) - 7 controls
    "MP": [
        ("MP.L2-3.8.1", "3.8.1", "Media Protection",
         "Protect (i.e., physically control and securely store) information system media containing CUI, both paper and digital."),

        ("MP.L2-3.8.2", "3.8.2", "Limit Access to CUI on Media",
         "Limit access to CUI on information system media to authorized users."),

        ("MP.L2-3.8.3", "3.8.3", "Media Disposal",
         "Sanitize or destroy information system media containing CUI before disposal or release for reuse."),

        ("MP.L2-3.8.4", "3.8.4", "Mark Media",
         "Mark media with necessary CUI markings and distribution limitations."),

        ("MP.L2-3.8.5", "3.8.5", "Control Access to Media",
         "Control access to media containing CUI and maintain accountability for media during transport outside of controlled areas."),

        ("MP.L2-3.8.6", "3.8.6", "Cryptographic Protection",
         "Implement cryptographic mechanisms to protect the confidentiality of CUI stored on digital media during transport unless otherwise protected by alternative physical safeguards."),

        ("MP.L2-3.8.7", "3.8.7", "Control Use of Removable Media",
         "Control the use of removable media on information system components."),

        ("MP.L2-3.8.8", "3.8.8", "Prohibit Use of Portable Storage",
         "Prohibit the use of portable storage devices when such devices have no identifiable owner."),

        ("MP.L2-3.8.9", "3.8.9", "Protect Backups",
         "Protect the confidentiality of backup CUI at storage locations."),
    ],

    # PERSONNEL SECURITY (PS) - 2 controls
    "PS": [
        ("PS.L2-3.9.1", "3.9.1", "Personnel Screening",
         "Screen individuals prior to authorizing access to organizational information systems containing CUI."),

        ("PS.L2-3.9.2", "3.9.2", "Ensure CUI Access Terminated",
         "Ensure that organizational information and information systems are protected during and after personnel actions such as terminations and transfers."),
    ],

    # PHYSICAL PROTECTION (PE) - 6 controls
    "PE": [
        ("PE.L2-3.10.1", "3.10.1", "Physical Access",
         "Limit physical access to organizational information systems, equipment, and the respective operating environments to authorized individuals."),

        ("PE.L2-3.10.2", "3.10.2", "Physical Access Authorizations",
         "Protect and monitor the physical facility and support infrastructure for organizational information systems."),

        ("PE.L2-3.10.3", "3.10.3", "Escort Visitors",
         "Escort visitors and monitor visitor activity."),

        ("PE.L2-3.10.4", "3.10.4", "Physical Access Logs",
         "Maintain audit logs of physical access."),

        ("PE.L2-3.10.5", "3.10.5", "Manage Physical Access",
         "Control and manage physical access devices."),

        ("PE.L2-3.10.6", "3.10.6", "Alternate Work Sites",
         "Enforce safeguards for CUI at alternate work sites."),
    ],

    # RISK ASSESSMENT (RA) - 3 controls
    "RA": [
        ("RA.L2-3.11.1", "3.11.1", "Risk Assessment",
         "Periodically assess the risk to organizational operations (including mission, functions, image, or reputation), organizational assets, and individuals, resulting from the operation of organizational information systems and the associated processing, storage, or transmission of CUI."),

        ("RA.L2-3.11.2", "3.11.2", "Vulnerability Scanning",
         "Scan for vulnerabilities in organizational information systems and applications periodically and when new vulnerabilities affecting those systems and applications are identified."),

        ("RA.L2-3.11.3", "3.11.3", "Remediate Vulnerabilities",
         "Remediate vulnerabilities in accordance with risk assessments."),
    ],

    # SECURITY ASSESSMENT (CA) - 9 controls
    "CA": [
        ("CA.L2-3.12.1", "3.12.1", "Security Assessment",
         "Periodically assess the security controls in organizational information systems to determine if the controls are effective in their application."),

        ("CA.L2-3.12.2", "3.12.2", "Plans of Action",
         "Develop and implement plans of action designed to correct deficiencies and reduce or eliminate vulnerabilities in organizational information systems."),

        ("CA.L2-3.12.3", "3.12.3", "System Interconnections",
         "Monitor security controls on an ongoing basis to ensure the continued effectiveness of the controls."),

        ("CA.L2-3.12.4", "3.12.4", "Security Impact Analysis",
         "Develop, document, and periodically update system security plans that describe system boundaries, system environments of operation, how security requirements are implemented, and the relationships with or connections to other systems."),
    ],

    # SYSTEM AND COMMUNICATIONS PROTECTION (SC) - 17 controls
    "SC": [
        ("SC.L2-3.13.1", "3.13.1", "Boundary Protection",
         "Monitor, control, and protect organizational communications (i.e., information transmitted or received by organizational information systems) at the external boundaries and key internal boundaries of the information systems."),

        ("SC.L2-3.13.2", "3.13.2", "Security Engineering Principles",
         "Implement subnetworks for publicly accessible system components that are physically or logically separated from internal networks."),

        ("SC.L2-3.13.3", "3.13.3", "Deny Network Traffic",
         "Deny network communications traffic by default and allow network communications traffic by exception (i.e., deny all, permit by exception)."),

        ("SC.L2-3.13.4", "3.13.4", "Network Disconnect",
         "Prevent unauthorized and unintended information transfer via shared system resources."),

        ("SC.L2-3.13.5", "3.13.5", "Split Tunneling",
         "Implement cryptographic mechanisms to prevent unauthorized disclosure of information and detect changes to information during transmission unless otherwise protected by alternative physical safeguards."),

        ("SC.L2-3.13.6", "3.13.6", "Network Disconnect",
         "Terminate network connections associated with communications sessions at the end of the sessions or after a defined period of inactivity."),

        ("SC.L2-3.13.7", "3.13.7", "Split Tunneling",
         "Establish and manage cryptographic keys for required cryptography employed in organizational information systems."),

        ("SC.L2-3.13.8", "3.13.8", "Transmission Confidentiality",
         "Employ FIPS-validated cryptography when used to protect the confidentiality of CUI."),

        ("SC.L2-3.13.9", "3.13.9", "Transmission Integrity",
         "Protect the authenticity of communications sessions."),

        ("SC.L2-3.13.10", "3.13.10", "Collaborative Computing Devices",
         "Protect the confidentiality of CUI at rest."),

        ("SC.L2-3.13.11", "3.13.11", "Cryptographic Key Management",
         "Employ architectural designs, software development techniques, and systems engineering principles that promote effective information security within organizational information systems."),

        ("SC.L2-3.13.12", "3.13.12", "Collaborative Computing Devices",
         "Separate user functionality from information system management functionality."),

        ("SC.L2-3.13.13", "3.13.13", "Mobile Code",
         "Deny network communications traffic by default and allow network communications traffic by exception (i.e., deny all, permit by exception)."),

        ("SC.L2-3.13.14", "3.13.14", "Voice Over IP",
         "Control and monitor the use of Voice over Internet Protocol (VoIP) technologies."),

        ("SC.L2-3.13.15", "3.13.15", "Collaborative Computing",
         "Protect the authenticity of communications sessions."),

        ("SC.L2-3.13.16", "3.13.16", "Transmission Confidentiality",
         "Protect the confidentiality of CUI at rest."),
    ],

    # SYSTEM AND INFORMATION INTEGRITY (SI) - 10 controls
    "SI": [
        ("SI.L2-3.14.1", "3.14.1", "Flaw Remediation",
         "Identify, report, and correct information and information system flaws in a timely manner."),

        ("SI.L2-3.14.2", "3.14.2", "Malicious Code Protection",
         "Provide protection from malicious code at appropriate locations within organizational information systems."),

        ("SI.L2-3.14.3", "3.14.3", "Security Alerts and Advisories",
         "Monitor information system security alerts and advisories and take action in response."),

        ("SI.L2-3.14.4", "3.14.4", "Update Malicious Code Protection",
         "Update malicious code protection mechanisms when new releases are available."),

        ("SI.L2-3.14.5", "3.14.5", "System and File Scanning",
         "Perform periodic scans of organizational information systems and real-time scans of files from external sources as files are downloaded, opened, or executed."),

        ("SI.L2-3.14.6", "3.14.6", "Monitor Communications for Attacks",
         "Monitor organizational information systems, including inbound and outbound communications traffic, to detect attacks and indicators of potential attacks."),

        ("SI.L2-3.14.7", "3.14.7", "Identify Unauthorized Use",
         "Identify unauthorized use of organizational information systems."),
    ],
}

def generate_sql():
    """Generate complete SQL seed file"""

    sql = [
        "-- ============================================================================",
        "-- CMMC Level 2 - Complete 110 Controls Seed Data",
        "-- Based on NIST SP 800-171 Revision 2",
        "-- CMMC Assessment Guide Version 2.13",
        "-- Generated: {}".format(__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "-- ============================================================================",
        "",
        "-- Clear existing controls",
        "DELETE FROM provider_inheritance;",
        "DELETE FROM control_findings;",
        "DELETE FROM cmmc_controls;",
        "",
    ]

    total_controls = 0

    for domain, controls in CMMC_L2_CONTROLS.items():
        sql.append(f"-- ============================================================================")
        sql.append(f"-- {domain} - {len(controls)} controls")
        sql.append(f"-- ============================================================================")
        sql.append("")
        sql.append("INSERT INTO cmmc_controls (id, level, domain, practice_id, title, objective, nist_control_id) VALUES")

        for i, (control_id, practice_id, title, objective) in enumerate(controls):
            total_controls += 1
            comma = "," if i < len(controls) - 1 else ";"
            sql.append(f"('{control_id}', 2, '{domain}', '{practice_id}', '{title}', '{objective}', '{practice_id}'){comma}")

        sql.append("")

    # Add verification
    sql.extend([
        "-- Verification",
        "DO $$",
        "DECLARE",
        "    control_count INTEGER;",
        "    domain_count INTEGER;",
        "BEGIN",
        "    SELECT COUNT(*) INTO control_count FROM cmmc_controls WHERE level = 2;",
        "    SELECT COUNT(DISTINCT domain) INTO domain_count FROM cmmc_controls WHERE level = 2;",
        "    ",
        "    RAISE NOTICE '✅ Imported % CMMC Level 2 controls across % domains', control_count, domain_count;",
        "    ",
        "    IF control_count != 110 THEN",
        "        RAISE EXCEPTION 'Expected 110 controls, found %', control_count;",
        "    END IF;",
        "    ",
        "    IF domain_count != 14 THEN",
        "        RAISE EXCEPTION 'Expected 14 domains, found %', domain_count;",
        "    END IF;",
        "END $$;",
    ])

    return '\n'.join(sql)

if __name__ == "__main__":
    output_path = "../database/seeds/01_cmmc_controls_complete.sql"

    print("🚀 Generating Complete CMMC Level 2 Controls...")

    sql_content = generate_sql()

    with open(output_path, 'w') as f:
        f.write(sql_content)

    # Count controls
    total = sum(len(controls) for controls in CMMC_L2_CONTROLS.values())

    print(f"✅ Generated: {output_path}")
    print(f"📊 Statistics:")
    print(f"   - Total Controls: {total}")
    print(f"   - Domains: {len(CMMC_L2_CONTROLS)}")
    print("")
    print("📋 Controls by Domain:")
    for domain, controls in CMMC_L2_CONTROLS.items():
        print(f"   - {domain}: {len(controls)} controls")
    print("")
    print("🔧 To import:")
    print(f"   psql -d cmmc_platform -f {output_path}")
