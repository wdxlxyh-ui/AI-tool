#!/usr/bin/env python3
"""
Azure Blob Storage 工具
提供 Blob 文件存在性检查、元数据获取等功能
"""
import os
import requests
import sys
from pathlib import Path
from typing import Dict, Optional


class AzureBlobClient:
    """Azure Blob Storage 客户端"""

    def __init__(self, account_name: str = "edgeadls2", blob_base: str = "https://edgeadls2.blob.core.chinacloudapi.cn/edge"):
        self.account_name = account_name
        self.blob_base = blob_base

    def check_file_exists_with_head(self, container_name: str, blob_path: str, sas_token: str) -> Optional[Dict]:
        """
        使用 HEAD 请求检查文件是否存在（可靠的方式）

        Args:
            container_name: 容器名称，如 "edge"
            blob_path: Blob 路径，如 "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"
            sas_token: SAS 令牌

        Returns:
            dict: 包含文件信息，失败返回 None
            {
                'exists': bool,
                'size': int,
                'content_type': str,
                'last_modified': str
            }
        """
        full_url = f"{self.blob_base}/{container_name}/{blob_path}?{sas_token}"

        try:
            response = requests.head(full_url, timeout=10)

            if response.status_code == 200:
                return {
                    'exists': True,
                    'size': int(response.headers.get('Content-Length', '0').strip()),
                    'content_type': response.headers.get('Content-Type', ''),
                    'last_modified': response.headers.get('Last-Modified', ''),
                    'etag': response.headers.get('ETag', '')
                }
            elif response.status_code == 404:
                return {'exists': False, 'size': 0, 'reason': 'Not Found'}
            else:
                return {'exists': False, 'size': 0, 'reason': f'Status {response.status_code}'}

        except Exception as e:
            return {'exists': False, 'size': 0, 'reason': f'Exception: {str(e)}'}

    def get_file_stat(self, blob_path: str, sas_token: str) -> Optional[Dict]:
        """
        获取文件详细信息

        Args:
            blob_path: Blob 路径
            sas_token: SAS 令牌

        Returns:
            dict: 文件信息，失败返回 None
        """
        return self.check_file_exists_with_head('edge', blob_path, sas_token)

    def list_directory(self, prefix: str, sas_token: str) -> list:
        """
        列出目录下的文件

        Args:
            prefix: 前缀路径，如 "edgeftpfile/edge-ems/develop_2605/"
            sas_token: SAS 令牌

        Returns:
            list: 文件列表
        """
        full_url = f"https://{self.account_name}.blob.core.chinacloudapi.cn/edge?restype=container&comp=list&prefix={prefix}{sas_token}"

        try:
            response = requests.get(full_url, timeout=15)

            if response.status_code == 200:
                # 解析 XML 响应（简化版，提取 BlobName）
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)

                blobs = []
                for entry in root.findall('{http://docs.oasis-open.org/ns/storage/2012/12}Entries') or root.findall('.//{http://docs.oasis-open.org/ns/storage/2012/12}Blob'):
                    name = entry.find('{http://docs.oasis-open.org/ns/storage/2012/12}BlobName')
                    if name is not None:
                        blobs.append(name.text)

                return blobs
            else:
                print(f"❌ 列出目录失败: {response.status_code}", file=sys.stderr)
                return []

        except Exception as e:
            print(f"❌ 列出目录失败: {e}", file=sys.stderr)
            return []


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Azure Blob Storage 工具")
    parser.add_argument("--check", required=True, help="Blob 路径，如 'edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz'")
    parser.add_argument("--list", help="列出目录下的文件（拼接 prefix）")

    args = parser.parse_args()

    # Get SAS token from environment
    sas_token = os.environ.get("AZURE_BLOB_SAS_TOKEN")
    if not sas_token:
        print("❌ AZURE_BLOB_SAS_TOKEN 未设置", file=sys.stderr)
        sys.exit(1)

    print("="*70)
    print("Azure Blob Storage 工具")
    print("="*70)
    print(f"Blob 路径: {args.check}")
    print()

    client = AzureBlobClient()

    if args.list:
        print(f"📂 列出目录: {args.list}")
        files = client.list_directory(args.list, sas_token)
        if files:
            print(f"✅ 找到 {len(files)} 个文件:")
            for f in sorted(files):
                print(f"   - {f}")
        else:
            print("❌ 没有找到文件")
    else:
        print("🔍 检查文件是否存在...")
        result = client.check_file_exists_with_head('edge', args.check, sas_token)

        if result['exists']:
            print(f"✅ 文件存在")
            print(f"   大小: {result['size'] / 1024 / 1024:.2f} MB")
            print(f"   Content-Type: {result['content_type']}")
            print(f"   最后修改: {result['last_modified']}")
        else:
            print(f"❌ 文件不存在: {result.get('reason', 'Unknown error')}")


if __name__ == "__main__":
    main()
