class WaitingQueue(list):
    total = 0

    def enqueue(self, x):
        WaitingQueue.total += 1
        self.append(x)

    def dequeue(self, x=None):
        if x is None:
            x = self.pop(0)
            WaitingQueue.total -= 1
        else:
            # attempt to remove the passed in item from the queue
            idx = self.index(x)
            if idx is not None:
                self.pop(idx)
                WaitingQueue.total -= 1
        return x


class Channel:
    def __init__(self):
        self.closed = False
        self.waiting_to_send = WaitingQueue()
        self.waiting_to_recv = WaitingQueue()


execution_queue = []


def go(cb):
    if cb:
        execution_queue.append(cb)


def run():
    while execution_queue:
        cb = execution_queue.pop()
        cb()

    if WaitingQueue.total > 0:
        raise Exception("fatal error: all goroutines are asleep - deadlock")


def make() -> Channel:
    return Channel()


def len(channel: Channel) -> int:
    return 0


def cap(channel: Channel) -> int:
    return 0


def send(channel, value, callback):
    # "A send on a nil channel blocks forever."
    if channel is None:
        WaitingQueue.total += 1
        return

    # "A send on a closed channel proceeds by causing a run-time panic."
    if channel.closed:
        raise Exception("send on closed channel")

    # "A send on an unbuffered channel can proceed if a receiver is ready."
    if channel.waiting_to_recv:
        receiver = channel.waiting_to_recv.dequeue()
        go(callback)
        go(lambda: receiver(value, True))
        return

    channel.waiting_to_send.enqueue((value, callback))


def recv(channel, callback):
    # "Receiving from a nil channel blocks forever."
    if channel is None:
        WaitingQueue.total += 1
        return

    # "if anything is currently blocked on sending for this channel, receive it"
    if channel.waiting_to_send:
        value, sender = channel.waiting_to_send.dequeue()
        go(lambda: callback(value, True))
        go(sender)
        return

    # "A receive operation on a closed channel can always proceed immediately,
    # yielding the element type's zero value after any previously sent values have been received."
    if channel.closed:
        go(lambda: callback(None, False))
        return

    channel.waiting_to_recv.enqueue(callback)


def close(channel):
    # if the channel is already closed, we panic
    if channel.closed:
        raise Exception("close of closed channel")

    channel.closed = True

    # complete any senders
    while channel.waiting_to_send:
        value, callback = channel.waiting_to_send.dequeue()
        send(channel, value, callback)

    # complete any receivers
    while channel.waiting_to_recv:
        callback = channel.waiting_to_recv.dequeue()
        recv(channel, callback)


go(lambda: print("test"))
go(lambda: print("1"))
go(lambda: print("2"))
go(lambda: print("3"))
run()
