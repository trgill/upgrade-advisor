# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""VM-based automated testing framework for OS upgrades."""

__version__ = "0.1.0"

from .vm_manager import VMManager, VMTemplate, VMInstance
from .test_matrix import TestMatrix, TestCase
from .test_runner import TestRunner, TestResult
from .reporting import TestReporter

__all__ = [
    'VMManager',
    'VMTemplate',
    'VMInstance',
    'TestMatrix',
    'TestCase',
    'TestRunner',
    'TestResult',
    'TestReporter',
]
