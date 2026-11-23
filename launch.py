import sys
from portable_launcher import main
if __name__=='__main__':
    sys.argv.insert(1,'--stage1')
    raise SystemExit(main())
