// SPDX-FileCopyrightText: 2022 Pepijn de Vos
//
// SPDX-License-Identifier: MPL-2.0

#include <string> 

#include "api/Simulator.capnp.h"
#include <kj/debug.h>
#include <kj/filesystem.h>
#include <kj/exception.h>
#include <kj/async-io.h>
#include <capnp/message.h>
#include <capnp/rpc-twoparty.h>

#include "../simserver.h"

#include <boost/asio.hpp>
#include <boost/process.hpp>
#include <boost/dll.hpp>
#include <boost/process/handles.hpp>
#include <boost/process/extend.hpp>

class SimulatorImpl final : public Sim::Simulator<SimCommands>::Server
{
public:
    SimulatorImpl(const kj::Directory &dir) : dir(dir) {}

    kj::Promise<void> loadFiles(LoadFilesContext context) override
    {
        auto files = context.getParams().getFiles();
        for (Sim::File::Reader f : files)
        {
            kj::Path path = kj::Path::parse(f.getName());
            kj::Own<const kj::File> file = dir.openFile(path, kj::WriteMode::CREATE | kj::WriteMode::MODIFY | kj::WriteMode::CREATE_PARENT);
            file->truncate(0);
            file->write(0, f.getContents());
        }

        std::string name = files[0].getName();

        auto res = context.getResults();
        auto commands = kj::heap<SimCommandsImpl>(name);
        res.setCommands(kj::mv(commands));
        return kj::READY_NOW;
    }

    kj::Promise<void> loadPath(LoadPathContext context) override
    {
        auto file = context.getParams().getFile();
        auto res = context.getResults();
        auto commands = kj::heap<SimCommandsImpl>(file);
        res.setCommands(kj::mv(commands));
        return kj::READY_NOW;
    }

    const kj::Directory &dir;
};

using boost::this_process::native_handle_type;

int runchild(kj::LowLevelAsyncIoProvider::Fd fd) {
    kj::AsyncIoContext ctx = kj::setupAsyncIo();
    auto stream = ctx.lowLevelProvider->wrapSocketFd(fd);
    auto network = capnp::TwoPartyVatNetwork(*stream, capnp::rpc::twoparty::Side::SERVER);
    kj::Own<kj::Filesystem> fs = kj::newDiskFilesystem();
    const kj::Directory &dir = fs->getCurrent();
    auto rpc = capnp::makeRpcServer(network, kj::heap<SimulatorImpl>(dir));
    network.onDisconnect().wait(ctx.waitScope);
    std::cout << "Client disconnected" << std::endl;
    return 0;
}

using namespace boost::asio;
using ip::tcp;
using namespace boost::process;
namespace ex = boost::process::extend;

struct do_inherit : boost::process::extend::handler
{
    template<typename Char, typename Sequence>
    void on_setup(ex::windows_executor<Char, Sequence> & exec)
    {
        std::cout << "windows setup" << std::endl;
        exec.inherit_handles = 1;
    }

    template<typename Sequence>
    void on_setup(ex::posix_executor<Sequence> & exec)
    {
        std::cout << "unix setup" << std::endl;
    }
};

int main(int argc, char const *argv[])
{
    int port = 5923;
    if (argc == 2 && strcmp(argv[1], "--help")==0) {
        std::cout << argv[0] << " [port]" << std::endl;
        return 0;
    } else if (argc == 3 && strcmp(argv[1], "--child")==0) {
        kj::LowLevelAsyncIoProvider::Fd fd = std::stoi(argv[2]);
        return runchild(fd);
    } else if (argc == 2)
    {
        port = std::stoi(argv[1]);
    }
    boost::filesystem::path p = boost::dll::program_location();
    boost::asio::io_service io_service;
    tcp::acceptor acceptor(io_service, tcp::endpoint(tcp::v6(), port));
    while (1)
    {
        std::cout << "waiting for clients" << std::endl;
        tcp::socket peersocket(io_service);
        acceptor.accept(peersocket);
        auto endpoint = peersocket.remote_endpoint();
        std::cout << "Accepted new connection from a client" << endpoint.address() << ":" << endpoint.port() << std::endl;
        std::string fd = std::to_string(peersocket.native_handle());
        boost::process::spawn(p, "--child", fd, do_inherit());
    }
    return 0;
}
