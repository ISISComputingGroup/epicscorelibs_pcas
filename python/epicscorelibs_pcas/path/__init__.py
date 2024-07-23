import os
import sysconfig


base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

include_path = os.path.join(sysconfig.get_paths()["include"], 'epicscorelibs_pcas')
lib_path = os.path.join(base_path, 'lib')
