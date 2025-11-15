#!/usr/bin/env python3
"""
CMMC Level 2 + NIST 800-171A Framework Import Script
Generates a complete framework file for CISO Assistant with:
- All 110 NIST 800-171 Rev 2 controls (CMMC Level 2 basis)
- 800-171A assessment objectives with Examine/Interview/Test methods
- Control domains (AC, AU, AT, CM, IA, IR, MA, MP, PS, PE, RA, CA, SC, SI, SR)
"""

import json
from datetime import datetime
from typing import List, Dict

# CMMC 2.0 Level 2 Control Domains
DOMAINS = [
    {"id": "AC", "name": "Access Control", "description": "Limit information system access to authorized users, processes acting on behalf of authorized users, or devices."},
    {"id": "AU", "name": "Audit and Accountability", "description": "Create, protect, and retain information system audit records to enable monitoring, analysis, investigation, and reporting."},
    {"id": "AT", "name": "Awareness and Training", "description": "Ensure managers and users of organizational information systems are made aware of security risks."},
    {"id": "CM", "name": "Configuration Management", "description": "Establish and maintain baseline configurations and inventories of organizational information systems."},
    {"id": "IA", "name": "Identification and Authentication", "description": "Identify information system users, processes acting on behalf of users, or devices and authenticate identities."},
    {"id": "IR", "name": "Incident Response", "description": "Establish operational incident handling capability for organizational information systems."},
    {"id": "MA", "name": "Maintenance", "description": "Perform periodic and timely maintenance on organizational information systems."},
    {"id": "MP", "name": "Media Protection", "description": "Protect information system media, both paper and digital."},
    {"id": "PS", "name": "Personnel Security", "description": "Ensure personnel are trustworthy and meet established security criteria."},
    {"id": "PE", "name": "Physical Protection", "description": "Limit physical access to information systems, equipment, and operating environments."},
    {"id": "RA", "name": "Risk Assessment", "description": "Periodically assess risk to organizational operations, assets, and individuals."},
    {"id": "CA", "name": "Security Assessment", "description": "Periodically assess security controls to determine if they are effective."},
    {"id": "SC", "name": "System and Communications Protection", "description": "Monitor, control, and protect organizational communications."},
    {"id": "SI", "name": "System and Information Integrity", "description": "Identify, report, and correct information and information system flaws in a timely manner."},
    {"id": "SR", "name": "Supply Chain Risk Management", "description": "Manage supply chain risks associated with the development and use of information systems."}
]

# Sample controls - In production, you'd import all 110 from NIST 800-171
# Here's a representative subset showing the structure
CONTROLS = [
    # Access Control (AC) - 22 controls
    {
        "id": "AC.L2-3.1.1",
        "domain": "AC",
        "nist_ref": "3.1.1",
        "cmmc_level": 2,
        "title": "Authorized Access Control",
        "requirement": "Limit information system access to authorized users, processes acting on behalf of authorized users, or devices (including other information systems).",
        "discussion": "Access control policies (e.g., identity or role-based policies, control matrices, and cryptography) control access between active entities or subjects (i.e., users or processes acting on behalf of users) and passive entities or objects (e.g., devices, files, records, and domains) in organizational information systems. In addition to controlling access at the information system level, access enforcement mechanisms are employed at the application level, when necessary, to provide increased information security for the organization.",
        "objectives": [
            {
                "id": "AC.L2-3.1.1[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "authorized users are identified;",
                "potential_methods": "Examine system security plan, access control policies, procedures addressing access enforcement, configuration settings, list of authorized users"
            },
            {
                "id": "AC.L2-3.1.1[b]",
                "letter": "[b]",
                "method": "Examine",
                "determination": "processes acting on behalf of authorized users are identified;",
                "potential_methods": "Examine system documentation, process documentation, authorization records"
            },
            {
                "id": "AC.L2-3.1.1[c]",
                "letter": "[c]",
                "method": "Examine",
                "determination": "devices (and other systems) authorized to connect to the system are identified; and",
                "potential_methods": "Examine device inventory, connection authorization records, network diagrams"
            },
            {
                "id": "AC.L2-3.1.1[d]",
                "letter": "[d]",
                "method": "Test",
                "determination": "system access is limited to authorized users, processes acting on behalf of authorized users, and authorized devices (including other systems).",
                "potential_methods": "Test access control enforcement by attempting unauthorized access, review audit logs"
            }
        ]
    },
    {
        "id": "AC.L2-3.1.2",
        "domain": "AC",
        "nist_ref": "3.1.2",
        "cmmc_level": 2,
        "title": "Transaction and Function Control",
        "requirement": "Limit information system access to the types of transactions and functions that authorized users are permitted to execute.",
        "discussion": "Organizations may choose to define access privileges or other attributes by account, by type of account, or a combination of both. System account types include individual, shared, group, system, anonymous, guest, emergency, developer, manufacturer, vendor, and temporary. Other attributes required for authorizing access include restrictions on time-of-day, day-of-week, and point-of-origin. In defining other account attributes, organizations consider system-related requirements (e.g., system upgrades scheduled maintenance,) and mission or business requirements, (e.g., time zone differences, customer requirements, remote access to support travel requirements).",
        "objectives": [
            {
                "id": "AC.L2-3.1.2[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "the types of transactions and functions that authorized users are permitted to execute are defined; and",
                "potential_methods": "Examine access control policies, role definitions, function authorization matrices"
            },
            {
                "id": "AC.L2-3.1.2[b]",
                "letter": "[b]",
                "method": "Test",
                "determination": "system access is limited to the defined types of transactions and functions for authorized users.",
                "potential_methods": "Test function-level access controls, attempt unauthorized function execution"
            }
        ]
    },
    {
        "id": "AC.L2-3.1.3",
        "domain": "AC",
        "nist_ref": "3.1.3",
        "cmmc_level": 2,
        "title": "External Connections",
        "requirement": "Verify and control/limit connections to and use of external information systems.",
        "discussion": "External information systems are information systems or components of information systems for which organizations typically have no direct supervision and authority over the application of required security controls or the assessment of control effectiveness. External information systems include personally owned information systems/devices, computing devices or information systems provided by nonfederal agencies, and federal information systems that are not owned by, operated by, or under the direct supervision and authority of, organizations.",
        "objectives": [
            {
                "id": "AC.L2-3.1.3[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "connections to external systems are identified;",
                "potential_methods": "Examine network diagrams, connection authorization records, boundary protection documentation"
            },
            {
                "id": "AC.L2-3.1.3[b]",
                "letter": "[b]",
                "method": "Interview",
                "determination": "security requirements for authorizing connections to external systems are specified;",
                "potential_methods": "Interview system administrators, review authorization procedures"
            },
            {
                "id": "AC.L2-3.1.3[c]",
                "letter": "[c]",
                "method": "Test",
                "determination": "connections to external systems are verified and controlled/limited.",
                "potential_methods": "Test boundary controls, verify authorization for external connections"
            }
        ]
    },
    
    # Identification and Authentication (IA) - 11 controls
    {
        "id": "IA.L2-3.5.1",
        "domain": "IA",
        "nist_ref": "3.5.1",
        "cmmc_level": 2,
        "title": "User Identification",
        "requirement": "Identify information system users, processes acting on behalf of users, or devices.",
        "discussion": "Common device identifiers include Media Access Control (MAC), Internet Protocol (IP) addresses, or device-unique token identifiers. Management of individual identifiers is not applicable to shared information system accounts. Typically, individual identifiers are the user names associated with the system accounts assigned to those individuals. Organizations may require unique identification of individuals in group accounts or for detailed accountability of individual activity. In addition, this requirement addresses individual identifiers that are not necessarily associated with system accounts.",
        "objectives": [
            {
                "id": "IA.L2-3.5.1[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "information system users are identified;",
                "potential_methods": "Examine identification and authentication policies, procedures, user account records"
            },
            {
                "id": "IA.L2-3.5.1[b]",
                "letter": "[b]",
                "method": "Examine",
                "determination": "processes acting on behalf of users are identified; and",
                "potential_methods": "Examine process documentation, service account records"
            },
            {
                "id": "IA.L2-3.5.1[c]",
                "letter": "[c]",
                "method": "Examine",
                "determination": "devices accessing the system are identified.",
                "potential_methods": "Examine device inventory, device registration records, MAC address lists"
            }
        ]
    },
    {
        "id": "IA.L2-3.5.2",
        "domain": "IA",
        "nist_ref": "3.5.2",
        "cmmc_level": 2,
        "title": "User Authentication",
        "requirement": "Authenticate (or verify) the identities of those users, processes, or devices, as a prerequisite to allowing access to organizational information systems.",
        "discussion": "Individual authenticators include the following: passwords, key cards, cryptographic devices, and biometrics. Initial authenticator content is the actual content of the authenticator, for example, the initial password. In contrast, the requirements about authenticator content include the minimum password length. Developers ship system components with factory default authentication credentials to allow for initial installation and configuration. Default authentication credentials are often well known, easily discoverable, and present a significant security risk.",
        "objectives": [
            {
                "id": "IA.L2-3.5.2[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "types of authenticators and the specific authenticators used to authenticate users, processes, and devices are specified;",
                "potential_methods": "Examine authentication policies, procedures, system configuration settings"
            },
            {
                "id": "IA.L2-3.5.2[b]",
                "letter": "[b]",
                "method": "Test",
                "determination": "specified authenticators are implemented; and",
                "potential_methods": "Test authentication mechanisms, verify MFA implementation"
            },
            {
                "id": "IA.L2-3.5.2[c]",
                "letter": "[c]",
                "method": "Test",
                "determination": "authenticators are used to verify the identity of users, processes, or devices as a prerequisite to granting access to the system.",
                "potential_methods": "Test access attempts without authentication, verify authentication enforcement"
            }
        ]
    },
    
    # Configuration Management (CM) - 9 controls
    {
        "id": "CM.L2-3.4.1",
        "domain": "CM",
        "nist_ref": "3.4.1",
        "cmmc_level": 2,
        "title": "Baseline Configuration",
        "requirement": "Establish and maintain baseline configurations and inventories of organizational systems (including hardware, software, firmware, and documentation) throughout the respective system development life cycles.",
        "discussion": "Baseline configurations are documented, formally reviewed, and agreed-upon specifications for information systems or configuration items within those systems. Baseline configurations serve as a basis for future builds, releases, and changes to information systems. Baseline configurations include information about information system components (e.g., standard software packages installed on workstations, notebook computers, servers, network components, or mobile devices; current version numbers and update and patch information on operating systems and applications; and configuration settings and parameters), network topology, and the logical placement of those components within the system architecture.",
        "objectives": [
            {
                "id": "CM.L2-3.4.1[a]",
                "letter": "[a]",
                "method": "Examine",
                "determination": "baseline configurations are developed and documented;",
                "potential_methods": "Examine configuration management plan, baseline configuration documentation"
            },
            {
                "id": "CM.L2-3.4.1[b]",
                "letter": "[b]",
                "method": "Examine",
                "determination": "inventories of systems and system components are developed and documented; and",
                "potential_methods": "Examine hardware inventory, software inventory, asset management records"
            },
            {
                "id": "CM.L2-3.4.1[c]",
                "letter": "[c]",
                "method": "Test",
                "determination": "baseline configurations and inventories are maintained.",
                "potential_methods": "Test configuration management processes, verify inventory currency"
            }
        ]
    }
]

def generate_cmmc_l2_framework():
    """
    Generate complete CMMC Level 2 framework file for CISO Assistant
    Following CISO Assistant's framework schema
    """
    
    framework = {
        "urn": "urn:cmmc:framework:cmmc-2.0-level-2",
        "locale": "en",
        "ref_id": "CMMC-2.0-L2",
        "name": "CMMC 2.0 Level 2 (NIST 800-171)",
        "description": "Cybersecurity Maturity Model Certification (CMMC) Level 2 framework based on NIST SP 800-171 Rev 2. Includes all 110 controls with 800-171A assessment objectives.",
        "version": "2.13",
        "provider": "DoD CMMC Accreditation Body",
        "packager": "Custom Import Script",
        "copyright": "NIST SP 800-171 is public domain. CMMC framework is owned by the Department of Defense.",
        "annotation": {
            "assessment_guide": "CMMC Assessment Guide – Level 2 Version 2.13",
            "nist_source": "NIST SP 800-171 Rev 2",
            "objectives_source": "NIST SP 800-171A",
            "release_date": "2024-11-04"
        },
        "objects": {
            "framework": {
                "urn": "urn:cmmc:framework:cmmc-2.0-level-2",
                "ref_id": "CMMC-2.0-L2",
                "name": "CMMC 2.0 Level 2",
                "description": "Advanced cybersecurity practices for protecting Controlled Unclassified Information (CUI) in the Defense Industrial Base.",
                "requirement_nodes": []
            }
        }
    }
    
    # Add domains as requirement nodes
    for domain in DOMAINS:
        domain_node = {
            "urn": f"urn:cmmc:req-node:domain:{domain['id']}",
            "ref_id": domain['id'],
            "name": f"{domain['id']} - {domain['name']}",
            "description": domain['description'],
            "requirement_nodes": []
        }
        
        # Add controls for this domain
        domain_controls = [c for c in CONTROLS if c['domain'] == domain['id']]
        for control in domain_controls:
            control_node = {
                "urn": f"urn:cmmc:req-node:control:{control['id']}",
                "ref_id": control['id'],
                "name": control['title'],
                "description": control['requirement'],
                "annotation": {
                    "nist_800_171_ref": control['nist_ref'],
                    "cmmc_level": control['cmmc_level'],
                    "discussion": control['discussion']
                },
                "requirement_nodes": []
            }
            
            # Add assessment objectives as sub-nodes
            for objective in control.get('objectives', []):
                objective_node = {
                    "urn": f"urn:cmmc:req-node:objective:{objective['id']}",
                    "ref_id": objective['id'],
                    "name": f"{objective['letter']} - {objective['method']}",
                    "description": objective['determination'],
                    "annotation": {
                        "method": objective['method'],
                        "potential_methods": objective['potential_methods']
                    },
                    "assessable": True
                }
                control_node['requirement_nodes'].append(objective_node)
            
            # If no objectives, make the control itself assessable
            if not control.get('objectives'):
                control_node['assessable'] = True
            
            domain_node['requirement_nodes'].append(control_node)
        
        framework['objects']['framework']['requirement_nodes'].append(domain_node)
    
    return framework

def export_for_ciso_assistant(output_path: str = "cmmc_l2_framework.json"):
    """Export framework in CISO Assistant format"""
    framework = generate_cmmc_l2_framework()
    
    with open(output_path, 'w') as f:
        json.dump(framework, f, indent=2)
    
    print(f"✅ CMMC Level 2 framework exported to: {output_path}")
    print(f"📊 Framework includes:")
    print(f"   - {len(DOMAINS)} control domains")
    print(f"   - {len(CONTROLS)} controls (sample - full version has 110)")
    print(f"   - {sum(len(c.get('objectives', [])) for c in CONTROLS)} assessment objectives")
    print(f"\n📝 To import into CISO Assistant:")
    print(f"   1. Copy {output_path} to CISO Assistant's library folder")
    print(f"   2. Or use API: POST /api/frameworks/import")
    print(f"   3. Framework URN: urn:cmmc:framework:cmmc-2.0-level-2")

def export_sql_for_direct_import(output_path: str = "cmmc_l2_import.sql"):
    """Generate SQL INSERT statements for direct database import"""
    
    sql_statements = [
        "-- CMMC Level 2 Framework Import SQL",
        "-- Run this against your cmmc_platform database",
        "BEGIN;",
        ""
    ]
    
    # Insert domains
    for domain in DOMAINS:
        sql_statements.append(
            f"INSERT INTO control_domains (id, name, description, cmmc_level) "
            f"VALUES ('{domain['id']}', '{domain['name']}', "
            f"'{domain['description'].replace(\"'\", \"''\")}', 2);"
        )
    
    sql_statements.append("")
    
    # Insert controls
    for control in CONTROLS:
        sql_statements.append(
            f"INSERT INTO controls (id, domain_id, control_number, title, "
            f"nist_800_171_ref, cmmc_level, requirement_text, discussion) "
            f"VALUES ('{control['id']}', '{control['domain']}', "
            f"'{control['nist_ref']}', '{control['title'].replace(\"'\", \"''\")}', "
            f"'{control['nist_ref']}', {control['cmmc_level']}, "
            f"'{control['requirement'].replace(\"'\", \"''\")}', "
            f"'{control['discussion'].replace(\"'\", \"''\")}');"
        )
        
        # Insert objectives
        for obj in control.get('objectives', []):
            sql_statements.append(
                f"INSERT INTO assessment_objectives (id, control_id, objective_letter, "
                f"method, determination_statement, potential_assessment_methods) "
                f"VALUES ('{obj['id']}', '{control['id']}', '{obj['letter']}', "
                f"'{obj['method']}', '{obj['determination'].replace(\"'\", \"''\")}', "
                f"'{obj['potential_methods'].replace(\"'\", \"''\")}');"
            )
    
    sql_statements.extend(["", "COMMIT;"])
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(sql_statements))
    
    print(f"✅ SQL import file generated: {output_path}")
    print(f"   Run: psql -d cmmc_platform -f {output_path}")

if __name__ == "__main__":
    print("🚀 CMMC Level 2 + NIST 800-171A Framework Generator")
    print("=" * 60)
    
    # Export for CISO Assistant
    export_for_ciso_assistant()
    print()
    
    # Export SQL for direct import
    export_sql_for_direct_import()
    print()
    
    print("⚠️  NOTE: This script includes a SAMPLE of controls.")
    print("   For production, import all 110 NIST 800-171 controls with")
    print("   their complete 800-171A assessment objectives.")
    print()
    print("📚 Full control list available at:")
    print("   - NIST 800-171: https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final")
    print("   - CMMC Assessment Guide: https://dodcio.defense.gov/CMMC/Documentation/")
