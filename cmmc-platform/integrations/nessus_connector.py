"""
Nessus Integration Connector
Hybrid approach supporting both:
1. Tenable.io / SecurityCenter (API-based)
2. Nessus Professional (file-based export)

Maps vulnerabilities to CMMC controls for evidence collection
"""

import asyncio
import asyncpg
import aiohttp
import xml.etree.ElementTree as ET
import csv
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)

class NessusConnector:
    """
    Connector for Nessus vulnerability scanner integration
    Supports both API and file-based ingestion
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.mode = config.get('mode', 'api')  # 'api' or 'file'
        
        if self.mode == 'api':
            self.base_url = config.get('base_url')
            self.access_key = config.get('access_key')
            self.secret_key = config.get('secret_key')
        else:
            self.export_path = Path(config.get('export_path', '/var/cmmc/nessus_exports'))
    
    # ============================================================================
    # CMMC CONTROL MAPPINGS
    # ============================================================================
    
    # Map plugin families to CMMC control domains
    PLUGIN_FAMILY_TO_DOMAIN = {
        'Backdoors': ['SC', 'SI'],  # System & Comm Protection, System Integrity
        'Brute force attacks': ['AC', 'IA'],  # Access Control, Identification & Auth
        'CGI abuses': ['SI', 'SC'],
        'CISCO': ['CM', 'SI'],  # Configuration Management
        'Databases': ['SC', 'CM'],
        'Default Unix Accounts': ['AC', 'IA', 'CM'],
        'Denial of Service': ['SC', 'SI'],
        'DNS': ['SC'],
        'Firewalls': ['SC', 'AC'],
        'FTP': ['SC', 'AC'],
        'Gain a shell remotely': ['AC', 'SC'],
        'General': ['RA'],  # Risk Assessment
        'Misc.': ['RA', 'SI'],
        'Netware': ['CM', 'AC'],
        'Port scanners': ['RA'],
        'RPC': ['SC'],
        'Service detection': ['RA', 'SI'],
        'Settings': ['CM', 'RA'],
        'SMTP problems': ['SC'],
        'SNMP': ['SC', 'AC'],
        'Web Servers': ['SC', 'SI', 'CM'],
        'Windows': ['CM', 'AC', 'SI'],
        'Windows : Microsoft Bulletins': ['SI', 'RA'],
        'Windows : User management': ['AC', 'IA']
    }
    
    # Map severity to CMMC risk levels
    SEVERITY_TO_RISK = {
        4: 'Critical',  # Critical
        3: 'High',
        2: 'Medium',
        1: 'Low',
        0: 'Info'
    }
    
    # Map vulnerability types to specific CMMC controls
    VULN_TO_CONTROLS = {
        # Configuration Management
        'missing_patch': ['SI.L2-3.14.1', 'SI.L2-3.14.2'],
        'weak_password': ['IA.L2-3.5.7', 'IA.L2-3.5.8'],
        'default_credentials': ['IA.L2-3.5.1', 'IA.L2-3.5.2'],
        'unnecessary_service': ['CM.L2-3.4.7', 'SC.L2-3.13.1'],
        'unencrypted_service': ['SC.L2-3.13.8', 'SC.L2-3.13.11'],
        
        # Access Control
        'unauthorized_access': ['AC.L2-3.1.1', 'AC.L2-3.1.2'],
        'privilege_escalation': ['AC.L2-3.1.5', 'AC.L2-3.1.6'],
        
        # System Integrity
        'malware': ['SI.L2-3.14.2', 'SI.L2-3.14.4'],
        'code_injection': ['SI.L2-3.14.3', 'SI.L2-3.14.5'],
        
        # Risk Assessment
        'vulnerability': ['RA.L2-3.11.2', 'RA.L2-3.11.3']
    }
    
    # ============================================================================
    # API-BASED INGESTION (Tenable.io / SecurityCenter)
    # ============================================================================
    
    async def fetch_scans_api(self) -> List[Dict]:
        """Fetch scans from Tenable API"""
        if self.mode != 'api':
            logger.error("API mode not configured")
            return []
        
        headers = {
            'X-ApiKeys': f'accessKey={self.access_key}; secretKey={self.secret_key}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            # Get list of scans
            async with session.get(
                f'{self.base_url}/scans',
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch scans: {response.status}")
                    return []
                
                data = await response.json()
                return data.get('scans', [])
    
    async def fetch_scan_details_api(self, scan_id: int) -> Dict:
        """Fetch detailed results for a specific scan"""
        headers = {
            'X-ApiKeys': f'accessKey={self.access_key}; secretKey={self.secret_key}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.base_url}/scans/{scan_id}',
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch scan details: {response.status}")
                    return {}
                
                return await response.json()
    
    # ============================================================================
    # FILE-BASED INGESTION (Nessus Professional)
    # ============================================================================
    
    def parse_nessus_xml(self, xml_path: Path) -> List[Dict]:
        """Parse .nessus XML export file"""
        vulnerabilities = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for report in root.findall('.//Report'):
                for host in report.findall('ReportHost'):
                    host_name = host.get('name')
                    
                    for item in host.findall('ReportItem'):
                        vuln = {
                            'host': host_name,
                            'port': item.get('port'),
                            'protocol': item.get('protocol'),
                            'service': item.get('svc_name'),
                            'plugin_id': item.get('pluginID'),
                            'plugin_name': item.get('pluginName'),
                            'plugin_family': item.get('pluginFamily'),
                            'severity': int(item.get('severity', 0)),
                            'risk_factor': item.findtext('risk_factor', 'None'),
                            'description': item.findtext('description', ''),
                            'solution': item.findtext('solution', ''),
                            'synopsis': item.findtext('synopsis', ''),
                            'plugin_output': item.findtext('plugin_output', ''),
                            'cvss_base_score': item.findtext('cvss_base_score', '0'),
                            'cvss_vector': item.findtext('cvss_vector', ''),
                            'cve': [cve.text for cve in item.findall('cve')],
                            'bid': [bid.text for bid in item.findall('bid')],
                            'see_also': [url.text for url in item.findall('see_also')]
                        }
                        
                        vulnerabilities.append(vuln)
            
            logger.info(f"Parsed {len(vulnerabilities)} vulnerabilities from {xml_path}")
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error parsing Nessus XML: {e}")
            return []
    
    def parse_nessus_csv(self, csv_path: Path) -> List[Dict]:
        """Parse Nessus CSV export"""
        vulnerabilities = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vuln = {
                        'host': row.get('Host'),
                        'port': row.get('Port'),
                        'protocol': row.get('Protocol'),
                        'service': row.get('Service'),
                        'plugin_id': row.get('Plugin ID'),
                        'plugin_name': row.get('Name'),
                        'plugin_family': row.get('Plugin Family'),
                        'severity': self._parse_severity(row.get('Risk')),
                        'risk_factor': row.get('Risk'),
                        'description': row.get('Description', ''),
                        'solution': row.get('Solution', ''),
                        'cvss_base_score': row.get('CVSS', '0')
                    }
                    vulnerabilities.append(vuln)
            
            logger.info(f"Parsed {len(vulnerabilities)} vulnerabilities from {csv_path}")
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error parsing Nessus CSV: {e}")
            return []
    
    def _parse_severity(self, risk: str) -> int:
        """Convert risk text to severity number"""
        risk_map = {
            'Critical': 4,
            'High': 3,
            'Medium': 2,
            'Low': 1,
            'None': 0,
            'Info': 0
        }
        return risk_map.get(risk, 0)
    
    # ============================================================================
    # CONTROL MAPPING
    # ============================================================================
    
    def map_vulnerability_to_controls(self, vuln: Dict) -> List[str]:
        """Map a vulnerability to relevant CMMC controls"""
        controls = set()
        
        # Map by plugin family
        family = vuln.get('plugin_family', '')
        if family in self.PLUGIN_FAMILY_TO_DOMAIN:
            domains = self.PLUGIN_FAMILY_TO_DOMAIN[family]
            # For now, return domain-level; in production, be more specific
            for domain in domains:
                # Add relevant controls for this domain
                controls.update(self._get_controls_for_domain(domain, vuln))
        
        # Map by vulnerability characteristics
        if 'password' in vuln.get('plugin_name', '').lower():
            controls.update(self.VULN_TO_CONTROLS.get('weak_password', []))
        
        if 'default' in vuln.get('plugin_name', '').lower():
            controls.update(self.VULN_TO_CONTROLS.get('default_credentials', []))
        
        if 'patch' in vuln.get('plugin_name', '').lower() or 'update' in vuln.get('plugin_name', '').lower():
            controls.update(self.VULN_TO_CONTROLS.get('missing_patch', []))
        
        if 'encryption' in vuln.get('plugin_name', '').lower() or 'ssl' in vuln.get('plugin_name', '').lower():
            controls.update(self.VULN_TO_CONTROLS.get('unencrypted_service', []))
        
        # If no specific mapping, map to general Risk Assessment
        if not controls:
            controls.add('RA.L2-3.11.2')  # Vulnerability scanning
        
        return list(controls)
    
    def _get_controls_for_domain(self, domain: str, vuln: Dict) -> List[str]:
        """Get specific controls for a domain based on vulnerability details"""
        # This is a simplified mapping - expand based on actual CMMC requirements
        domain_controls = {
            'AC': ['AC.L2-3.1.1', 'AC.L2-3.1.2', 'AC.L2-3.1.3'],
            'IA': ['IA.L2-3.5.1', 'IA.L2-3.5.2', 'IA.L2-3.5.7'],
            'CM': ['CM.L2-3.4.1', 'CM.L2-3.4.2', 'CM.L2-3.4.7'],
            'SC': ['SC.L2-3.13.1', 'SC.L2-3.13.8', 'SC.L2-3.13.11'],
            'SI': ['SI.L2-3.14.1', 'SI.L2-3.14.2', 'SI.L2-3.14.3'],
            'RA': ['RA.L2-3.11.2', 'RA.L2-3.11.3']
        }
        
        return domain_controls.get(domain, [])
    
    # ============================================================================
    # DATABASE INTEGRATION
    # ============================================================================
    
    async def ingest_to_database(
        self,
        vulnerabilities: List[Dict],
        assessment_id: str,
        conn: asyncpg.Connection
    ):
        """Ingest vulnerabilities as evidence into the database"""
        
        for vuln in vulnerabilities:
            # Skip info-level findings if configured
            if vuln['severity'] == 0 and not self.config.get('include_info', False):
                continue
            
            # Map to controls
            control_ids = self.map_vulnerability_to_controls(vuln)
            
            # Create evidence for each relevant control
            for control_id in control_ids:
                # Generate evidence content
                evidence_content = self._format_evidence_content(vuln)
                evidence_hash = hashlib.sha256(evidence_content.encode()).hexdigest()
                
                # Check if evidence already exists
                existing = await conn.fetchval(
                    "SELECT id FROM evidence WHERE file_hash = $1",
                    evidence_hash
                )
                
                if existing:
                    logger.debug(f"Evidence already exists: {evidence_hash[:8]}")
                    continue
                
                # Store evidence
                evidence_path = f"/var/cmmc/evidence/nessus/{evidence_hash[:2]}/{evidence_hash}"
                Path(evidence_path).parent.mkdir(parents=True, exist_ok=True)
                Path(evidence_path).write_text(evidence_content)
                
                # Insert evidence record
                await conn.execute(
                    """
                    INSERT INTO evidence 
                    (assessment_id, control_id, evidence_type, title, description,
                     method, file_path, file_hash, file_size_bytes, mime_type,
                     collected_by, collection_method, status)
                    VALUES ($1, $2, 'test_result', $3, $4, 'Test', $5, $6, $7, 'text/plain',
                            $8, 'api_nessus', 'approved')
                    """,
                    assessment_id,
                    control_id,
                    f"Nessus Finding: {vuln['plugin_name'][:100]}",
                    f"Host: {vuln['host']}, Severity: {vuln['risk_factor']}",
                    evidence_path,
                    evidence_hash,
                    len(evidence_content),
                    '00000000-0000-0000-0000-000000000000'  # System user
                )
                
                logger.info(f"Created evidence for {control_id}: {vuln['plugin_name'][:50]}")
                
                # Create POA&M item for High/Critical findings
                if vuln['severity'] >= 3:
                    await self._create_poam_item(vuln, control_id, assessment_id, conn)
    
    def _format_evidence_content(self, vuln: Dict) -> str:
        """Format vulnerability as evidence content"""
        return f"""
NESSUS VULNERABILITY FINDING
============================

Plugin ID: {vuln['plugin_id']}
Plugin Name: {vuln['plugin_name']}
Plugin Family: {vuln['plugin_family']}

Host: {vuln['host']}
Port: {vuln['port']}/{vuln.get('protocol', 'tcp')}
Service: {vuln.get('service', 'N/A')}

Risk Factor: {vuln['risk_factor']}
CVSS Base Score: {vuln.get('cvss_base_score', 'N/A')}
CVE: {', '.join(vuln.get('cve', [])) or 'None'}

DESCRIPTION:
{vuln.get('description', 'N/A')}

SYNOPSIS:
{vuln.get('synopsis', 'N/A')}

SOLUTION:
{vuln.get('solution', 'N/A')}

PLUGIN OUTPUT:
{vuln.get('plugin_output', 'N/A')}

SCAN DATE: {datetime.utcnow().isoformat()}
"""
    
    async def _create_poam_item(
        self,
        vuln: Dict,
        control_id: str,
        assessment_id: str,
        conn: asyncpg.Connection
    ):
        """Create POA&M item for high/critical findings"""
        
        # Check if POA&M already exists for this control
        existing = await conn.fetchval(
            """
            SELECT id FROM poam_items 
            WHERE assessment_id = $1 AND control_id = $2 
            AND weakness_description LIKE $3
            """,
            assessment_id,
            control_id,
            f"%{vuln['plugin_id']}%"
        )
        
        if existing:
            return
        
        # Get next POA&M ID
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM poam_items WHERE assessment_id = $1",
            assessment_id
        )
        poam_id = f"POA&M-{str(count + 1).zfill(3)}"
        
        await conn.execute(
            """
            INSERT INTO poam_items 
            (assessment_id, control_id, poam_id, weakness_description, 
             risk_level, remediation_plan, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'open')
            """,
            assessment_id,
            control_id,
            poam_id,
            f"Nessus Plugin {vuln['plugin_id']}: {vuln['plugin_name']} on {vuln['host']}",
            self.SEVERITY_TO_RISK.get(vuln['severity'], 'Medium'),
            vuln.get('solution', 'Review and remediate according to vendor guidance.')
        )

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """Example usage"""
    
    # API mode (Tenable.io / SecurityCenter)
    api_config = {
        'mode': 'api',
        'base_url': 'https://cloud.tenable.com',
        'access_key': 'your-access-key',
        'secret_key': 'your-secret-key'
    }
    
    # File mode (Nessus Professional)
    file_config = {
        'mode': 'file',
        'export_path': '/var/cmmc/nessus_exports'
    }
    
    # Use file mode for this example
    connector = NessusConnector(file_config)
    
    # Parse XML export
    nessus_file = Path('/var/cmmc/nessus_exports/scan_results.nessus')
    if nessus_file.exists():
        vulnerabilities = connector.parse_nessus_xml(nessus_file)
        
        # Connect to database and ingest
        conn = await asyncpg.connect('postgresql://user:pass@localhost/cmmc_platform')
        
        try:
            await connector.ingest_to_database(
                vulnerabilities,
                assessment_id='your-assessment-uuid',
                conn=conn
            )
        finally:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
