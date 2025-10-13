"""USB Certificate Verification Module."""

import os
import json
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass
class USBDeviceInfo:
    """USB device information from device_info.json."""
    device_id: str
    device_name: str
    firmware_version: str
    created_at: str
    target_device: str

@dataclass
class VerificationResult:
    """Result of USB verification."""
    success: bool
    message: str
    device_info: USBDeviceInfo = None
    firmware_path: str = None
    mount_point: str = None

class USBCertificateVerifier:
    """Verify USB device certificate and firmware integrity."""
    
    def __init__(self, public_key_path, config):
        """Initialize verifier.
        
        Args:
            public_key_path: Path to RSA public key
            config: Configuration dict
        """
        self.public_key_path = public_key_path
        self.config = config
        
        # Check if public key exists
        if not os.path.exists(public_key_path):
            print(f"[CertVerifier] ⚠️  Public key not found: {public_key_path}")
            print("[CertVerifier] Security disabled!")
            self.security_enabled = False
        else:
            print(f"[CertVerifier] ✓ Public key loaded: {public_key_path}")
            self.security_enabled = True
    
    def verify_usb_device(self, mount_point):
        """Verify USB device certificate and firmware.
        
        Args:
            mount_point: USB mount point path
            
        Returns:
            VerificationResult
        """
        print(f"\n{'='*60}")
        print(f"[CertVerifier] Verifying USB at: {mount_point}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Check file structure
            result = self._check_file_structure(mount_point)
            if not result.success:
                return result
            
            # Step 2: Load device info
            device_info = self._load_device_info(mount_point)
            if not device_info:
                return VerificationResult(
                    success=False,
                    message="Failed to load device_info.json"
                )
            
            print(f"[CertVerifier] Device: {device_info.device_name}")
            print(f"[CertVerifier] Target: {device_info.target_device}")
            print(f"[CertVerifier] Version: {device_info.firmware_version}")
            
            # Step 3: Verify certificate (if enabled)
            if self.security_enabled and self.config['security']['require_certificate']:
                result = self._verify_certificate(mount_point)
                if not result.success:
                    return result
            else:
                print("[CertVerifier] ⚠️  Certificate verification SKIPPED")
            
            # Step 4: Verify firmware checksum
            if self.config['security']['verify_checksum']:
                result = self._verify_firmware_checksum(mount_point)
                if not result.success:
                    return result
            else:
                print("[CertVerifier] ⚠️  Checksum verification SKIPPED")
            
            # All checks passed
            firmware_path = os.path.join(
                mount_point,
                self.config['firmware']['usb_path']
            )
            
            print(f"\n[CertVerifier] ✓ USB VERIFIED SUCCESSFULLY")
            print(f"[CertVerifier] Firmware ready: {firmware_path}")
            
            return VerificationResult(
                success=True,
                message="USB device verified successfully",
                device_info=device_info,
                firmware_path=firmware_path,
                mount_point=mount_point
            )
            
        except Exception as e:
            print(f"[CertVerifier] ✗ Verification error: {e}")
            import traceback
            traceback.print_exc()
            return VerificationResult(
                success=False,
                message=f"Verification error: {str(e)}"
            )
    
    def _check_file_structure(self, mount_point):
        """Check if USB has required files.
        
        Args:
            mount_point: USB mount point
            
        Returns:
            VerificationResult
        """
        print("\n[CertVerifier] Step 1: Checking file structure...")
        
        required_files = [
            self.config['firmware']['device_info_path'],
            self.config['firmware']['usb_path'],
        ]
        
        if self.config['security']['require_certificate']:
            required_files.append(self.config['firmware']['certificate_path'])
        
        if self.config['security']['verify_checksum']:
            required_files.append(self.config['firmware']['checksum_path'])
        
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(mount_point, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)
                print(f"[CertVerifier] ✗ Missing: {file_path}")
            else:
                print(f"[CertVerifier] ✓ Found: {file_path}")
        
        if missing_files:
            return VerificationResult(
                success=False,
                message=f"Missing required files: {', '.join(missing_files)}"
            )
        
        return VerificationResult(success=True, message="File structure OK")
    
    def _load_device_info(self, mount_point):
        """Load device_info.json.
        
        Args:
            mount_point: USB mount point
            
        Returns:
            USBDeviceInfo or None
        """
        print("\n[CertVerifier] Step 2: Loading device info...")
        
        try:
            info_path = os.path.join(
                mount_point,
                self.config['firmware']['device_info_path']
            )
            
            with open(info_path, 'r') as f:
                data = json.load(f)
            
            return USBDeviceInfo(
                device_id=data['device_id'],
                device_name=data['device_name'],
                firmware_version=data['firmware_version'],
                created_at=data['created_at'],
                target_device=data['target_device']
            )
        except Exception as e:
            print(f"[CertVerifier] ✗ Failed to load device info: {e}")
            return None
    
    def _verify_certificate(self, mount_point):
        """Verify digital signature of device_info.json.
        
        Args:
            mount_point: USB mount point
            
        Returns:
            VerificationResult
        """
        print("\n[CertVerifier] Step 3: Verifying certificate...")
        
        try:
            cert_path = os.path.join(
                mount_point,
                self.config['firmware']['certificate_path']
            )
            info_path = os.path.join(
                mount_point,
                self.config['firmware']['device_info_path']
            )
            
            # Use OpenSSL to verify signature
            cmd = [
                'openssl', 'dgst', '-sha256',
                '-verify', self.public_key_path,
                '-signature', cert_path,
                info_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("[CertVerifier] ✓ Certificate VERIFIED")
                return VerificationResult(
                    success=True,
                    message="Certificate verified"
                )
            else:
                print(f"[CertVerifier] ✗ Certificate verification FAILED")
                print(f"[CertVerifier] Error: {result.stderr}")
                return VerificationResult(
                    success=False,
                    message="Invalid certificate signature"
                )
                
        except subprocess.TimeoutExpired:
            return VerificationResult(
                success=False,
                message="Certificate verification timeout"
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                message=f"Certificate verification error: {str(e)}"
            )
    
    def _verify_firmware_checksum(self, mount_point):
        """Verify firmware file checksum.
        
        Args:
            mount_point: USB mount point
            
        Returns:
            VerificationResult
        """
        print("\n[CertVerifier] Step 4: Verifying firmware checksum...")
        
        try:
            firmware_path = os.path.join(
                mount_point,
                self.config['firmware']['usb_path']
            )
            checksum_path = os.path.join(
                mount_point,
                self.config['firmware']['checksum_path']
            )
            
            # Read expected checksum
            with open(checksum_path, 'r') as f:
                expected_checksum = f.read().strip()
            
            print(f"[CertVerifier] Expected: {expected_checksum}")
            
            # Calculate actual checksum
            actual_checksum = self._calculate_sha256(firmware_path)
            print(f"[CertVerifier] Actual:   {actual_checksum}")
            
            if actual_checksum == expected_checksum:
                print("[CertVerifier] ✓ Checksum MATCHED")
                return VerificationResult(
                    success=True,
                    message="Firmware checksum verified"
                )
            else:
                print("[CertVerifier] ✗ Checksum MISMATCH")
                return VerificationResult(
                    success=False,
                    message="Firmware checksum mismatch - file may be corrupted"
                )
                
        except Exception as e:
            return VerificationResult(
                success=False,
                message=f"Checksum verification error: {str(e)}"
            )
    
    def _calculate_sha256(self, file_path):
        """Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex string of hash
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()