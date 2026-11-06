PYTHON ?= python3
.DEFAULT_GOAL := all

.PHONY: all FORCE
FORCE:

all: ../daemon/ui/protocol/ui.pb.go ../ui/opensnitch/proto/ui_pb2.py

../daemon/ui/protocol/ui.pb.go: ui.proto FORCE
	protoc -I. ui.proto --go_out=../daemon/ui/protocol/ --go-grpc_out=../daemon/ui/protocol/ --go_opt=paths=source_relative --go-grpc_opt=paths=source_relative

../ui/opensnitch/proto/ui_pb2.py: ui.proto FORCE
	$(PYTHON) -m grpc_tools.protoc -I. --python_out=../ui/opensnitch/proto/ --pyi_out=../ui/opensnitch/proto/ --grpc_python_out=../ui/opensnitch/proto/ ui.proto
	sed -i 's/^import ui_pb2/from . import ui_pb2/' ../ui/opensnitch/proto/ui_pb2_grpc.py

clean:
	@rm -rf ../daemon/ui/protocol/ui.pb.go
	@rm -rf ../daemon/ui/protocol/ui_grpc.pb.go
	@rm -rf ../ui/opensnitch/proto/ui_pb2.py
	@rm -rf ../ui/opensnitch/proto/ui_pb2_grpc.py
	@rm -rf ../ui/opensnitch/proto/ui_pb2.pyi
